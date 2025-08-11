"""
Context Merger v4 — interactive sources, real collectors (RSS, Trends, DESTATIS, SERP),
clean registry (ohne Notion/GDrive), scoring & provenance
-----------------------------------------------------------------------------------
Workflow:
 1) reason_before_merge()  → erstellt Plan + Vorschläge für Datenquellen (ohne Fetch)
 2) collect_context_after_confirmation(selected_sources?, source_params?)
    → sammelt NUR bestätigte Quellen + merged_context + provenance
 3) get_final_context_bundle() → fasst zusammen und liefert Feldvorschläge

Neu in v4:
- DESTATIS (GENESIS REST) Collector mit echtem API-Call (table-ID)
- SERP Collector mit echtem API-Call (SerpAPI oder Bing Web Search)
- Notion/GDrive vollständig entfernt
- Stabilere Fehlerbehandlung, kleine Token-Schonung

Hinweise:
- Lighthouse bleibt außerhalb (Base-Agent-Task). Der Merger kann Ergebnisse später
  wieder aufnehmen.
- Für externe APIs werden ENV-Variablen erwartet; ohne Konfiguration liefern Collector
  einen freundlichen Hinweis-Chunk mit meta={"type":"error"}.
- DESTATIS: Für produktive Nutzung empfiehlt sich ein eigener Account (siehe Doku). Ohne
  Credentials schlägt der Collector "freundlich" fehl.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from langchain_openai import ChatOpenAI

# === Local deps (existing project helpers) ===
from agent.customer_memory import load_customer_memory
from agent.loader import load_pdf, extract_seo_signals
from agent.tools.scraper import scrape_html
from agent.tools.parser import extract_text_blocks

# Optional dependency – keep safe import
try:
    from agent.knowledge.guidelines import get_general_guidelines
except Exception:  # pragma: no cover
    def get_general_guidelines() -> str:
        return ""

from agent.prompts import (
    context_merger_planner_prompt,
    context_merger_executor_prompt,
)

# ---------------------------
# Model setup
# ---------------------------
llm = ChatOpenAI(model="gpt-4o", max_tokens=3000)

# ---------------------------
# Data contracts
# ---------------------------
@dataclass
class ContextChunk:
    source: str  # e.g. "customer:ID", "url:https://...", "pdf:path", "guidelines", "rss:<feed>", ...
    content: str
    score: float = 0.0
    meta: Dict[str, Any] = None  # {category:"rss|trends|onpage|...", ..}

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["preview"] = (self.content or "")[:240]
        return d


# ---------------------------
# Utility helpers
# ---------------------------

def _safe_json_parse(raw: str) -> Dict[str, Any]:
    if not raw or not isinstance(raw, str):
        return {"raw_response": str(raw)}
    txt = raw.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z0-9_-]*\n|```$", "", txt).strip()
    m = re.search(r"\{[\s\S]*\}", txt)
    candidate = m.group(0) if m else txt
    candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
    try:
        return json.loads(candidate)
    except Exception:
        return {"raw_response": raw}


def _token_estimate(text: str) -> int:
    return math.ceil(len(text) / 4)


def _hash_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _keyword_score(text: str, keywords: Iterable[str]) -> float:
    if not text or not keywords:
        return 0.0
    txt = text.lower()
    hits = sum(1 for k in keywords if k and k.lower() in txt)
    return hits / max(1, len(list(keywords)))


def _dedup_chunks(chunks: List[ContextChunk], similarity_threshold: float = 0.92) -> List[ContextChunk]:
    seen: Dict[str, ContextChunk] = {}
    for ch in chunks:
        norm = re.sub(r"\s+", " ", ch.content or "").strip().lower()
        key = _hash_text(norm)
        if key not in seen:
            seen[key] = ch
    return list(seen.values())


def _truncate_to_token_budget(text: str, max_tokens: int) -> str:
    if _token_estimate(text) <= max_tokens:
        return text
    parts = re.split(r"\n\s*\n", text)
    out: List[str] = []
    for p in parts:
        out.append(p)
        if _token_estimate("\n\n".join(out)) > max_tokens:
            out.pop()
            break
    return "\n\n".join(out)


# ---------------------------
# Category weights (per Task later if needed)
# ---------------------------
CATEGORY_WEIGHTS: Dict[str, float] = {
    "customer": 1.00,
    "guidelines": 0.60,
    "url": 0.70,
    "pdf": 0.70,
    "onpage": 0.80,
    "sitemap": 0.40,
    "rss": 0.55,
    "trends": 0.45,
    "destatis": 0.60,
    "ads": 0.50,
    "serp": 0.55,
    "competitors": 0.60,
}


# ---------------------------
# Source collectors
# ---------------------------
class SourceCollector:
    id: str = "base"
    label: str = "Base"
    category: str = "misc"

    def __init__(self, **params: Any) -> None:
        self.params = params

    def collect(self) -> List[ContextChunk]:  # pragma: no cover (interface)
        raise NotImplementedError

    def _chunk(self, source: str, content: str, **meta) -> ContextChunk:
        md = {"category": self.category, **meta}
        return ContextChunk(source=source, content=content, meta=md)


class CustomerMemoryCollector(SourceCollector):
    id = "customer_memory"
    label = "Kunden-Gedächtnis"
    category = "customer"

    def collect(self) -> List[ContextChunk]:
        cid = self.params.get("customer_id")
        if not cid:
            return []
        try:
            mem = load_customer_memory(cid)
            if not mem:
                return []
            return [self._chunk(f"customer:{cid}", mem)]
        except Exception as e:
            return [self._chunk(f"customer:{cid}", f"[Fehler beim Laden des Kundengedächtnisses: {e}]", type="error")]


class UrlCollector(SourceCollector):
    id = "url"
    label = "Website (Inhalt)"
    category = "url"

    def collect(self) -> List[ContextChunk]:
        url = (self.params.get("url") or "").strip()
        if not url:
            return []
        try:
            html = scrape_html(url)
            blocks = extract_text_blocks(html)
            text = "\n".join(blocks)
            return [self._chunk(f"url:{url}", text)]
        except Exception as e:
            return [self._chunk(f"url:{url}", f"[Fehler beim Laden der URL: {e}]", type="error")]


class PdfCollector(SourceCollector):
    id = "pdf"
    label = "PDF"
    category = "pdf"

    def collect(self) -> List[ContextChunk]:
        pdf_path = self.params.get("pdf_path")
        if not pdf_path:
            return []
        try:
            pdf_text = load_pdf(pdf_path)
            return [self._chunk(f"pdf:{pdf_path}", pdf_text)]
        except Exception as e:
            return [self._chunk(f"pdf:{pdf_path}", f"[Fehler beim Laden der PDF: {e}]", type="error")]


class GuidelinesCollector(SourceCollector):
    id = "guidelines"
    label = "Guidelines/Playbooks"
    category = "guidelines"

    def collect(self) -> List[ContextChunk]:
        try:
            g = get_general_guidelines()
            return [self._chunk("guidelines", g)] if g else []
        except Exception as e:
            return [self._chunk("guidelines", f"[Fehler beim Laden der Guidelines: {e}]", type="error")]


# A) News/Trends/Stats/Ads ----------------------------------------------------
class RssCollector(SourceCollector):
    id = "rss"
    label = "RSS/News"
    category = "rss"

    def collect(self) -> List[ContextChunk]:
        feeds: List[str] = self.params.get("feeds") or []
        keywords: List[str] = self.params.get("keywords") or []
        days: int = int(self.params.get("days", 14))
        if not feeds:
            return []
        try:
            import feedparser  # type: ignore
        except Exception:
            return [self._chunk("rss", "[feedparser nicht installiert]", type="error")]
        out: List[ContextChunk] = []
        now = time.time()
        earliest = now - days * 86400
        for f in feeds:
            try:
                parsed = feedparser.parse(f)
                for e in parsed.get("entries", [])[:100]:
                    published = e.get("published_parsed")
                    ts = time.mktime(published) if published else now
                    if ts < earliest:
                        continue
                    title = e.get("title", "")
                    summary = re.sub(r"<[^>]+>", " ", e.get("summary", ""))
                    link = e.get("link", "")
                    text = f"{title}\n{summary}\n{link}"
                    if keywords and not any(k.lower() in text.lower() for k in keywords):
                        continue
                    out.append(self._chunk(f"rss:{f}", text, url=link))
            except Exception as ex:
                out.append(self._chunk(f"rss:{f}", f"[RSS Fehler: {ex}]", type="error"))
        return out


class TrendsCollector(SourceCollector):
    id = "trends"
    label = "Google Trends"
    category = "trends"

    def collect(self) -> List[ContextChunk]:
        kw_list: List[str] = self.params.get("keywords") or []
        geo: str = self.params.get("geo", "DE")
        timeframe: str = self.params.get("timeframe", "today 3-m")
        try:
            from pytrends.request import TrendReq  # type: ignore
        except Exception:
            return [self._chunk("trends", "[pytrends nicht installiert]", type="error")]
        try:
            if not kw_list:
                return []
            pt = TrendReq(hl="de-DE", tz=60)
            pt.build_payload(kw_list, timeframe=timeframe, geo=geo)
            df = pt.interest_over_time()
            if df is None or df.empty:
                return []
            # kleine, robuste Zusammenfassung
            tail = df.tail(min(12, len(df)))
            csv_snip = tail.to_csv(index=True)
            lines = [
                "Google Trends — Interest over time",
                csv_snip[:4000],
            ]
            return [self._chunk("trends", "\n".join(lines), geo=geo, timeframe=timeframe, keywords=kw_list)]
        except Exception as e:
            return [self._chunk("trends", f"[Trends Fehler: {e}]", type="error")]


class DestatisCollector(SourceCollector):
    id = "destatis"
    label = "DESTATIS/Statistik"
    category = "destatis"

    def collect(self) -> List[ContextChunk]:
        table: str = (self.params.get("table") or self.params.get("query") or "").strip()
        if not table:
            return []
        import requests

        token = os.getenv("DESTATIS_TOKEN")
        username = os.getenv("DESTATIS_USERNAME")
        password = os.getenv("DESTATIS_PASSWORD")

        base = "https://www-genesis.destatis.de/genesisWS/rest/2020/data/table"
        body = {"name": table, "area": "all", "compress": "false", "language": "de"}

        def _try(headers=None, auth=None):
            try:
                r = requests.post(base, data=body, headers=headers or {}, auth=auth, timeout=30)
                return r.status_code, r.text
            except Exception as e:
                return 599, f"[HTTP Fehler: {e}]"

        # 1) Token bevorzugt
        if token:
            # a) Bearer (häufigste Form)
            code, txt = _try(headers={"Authorization": f"Bearer {token}"})
            if code == 200:
                return [self._chunk(f"destatis:{table}", txt[:18000], table=table)]
            # b) X-API-Token (einige Installationen)
            code, txt = _try(headers={"X-API-Token": token})
            if code == 200:
                return [self._chunk(f"destatis:{table}", txt[:18000], table=table)]
            # c) Basic mit Token als Nutzer (Fallback)
            from requests.auth import HTTPBasicAuth
            code, txt = _try(auth=HTTPBasicAuth(token, ""))
            if code == 200:
                return [self._chunk(f"destatis:{table}", txt[:18000], table=table)]
            return [self._chunk(f"destatis:{table}", f"[DESTATIS Token konnte nicht verwendet werden, HTTP {code}] {txt[:400]}", type="error")]

        # 2) Username/Passwort (falls vorhanden)
        if username and password:
            code, txt = _try(auth=(username, password))
            if code == 200:
                return [self._chunk(f"destatis:{table}", txt[:18000], table=table)]
            return [self._chunk(f"destatis:{table}", f"[DESTATIS HTTP {code}] {txt[:400]}", type="error")]

        return [self._chunk("destatis", "[DESTATIS nicht konfiguriert: Bitte DESTATIS_TOKEN oder USERNAME/PASSWORD setzen]", type="error", table=table)]


class AdsCollector(SourceCollector):
    id = "ads"
    label = "Ads-Bibliotheken (Meta/Google/LinkedIn)"
    category = "ads"

    def collect(self) -> List[ContextChunk]:
        terms: List[str] = self.params.get("terms") or []
        platform: str = self.params.get("platform", "meta")
        if not terms:
            return []
        joined = ", ".join(terms)
        return [self._chunk(f"ads:{platform}", f"[Ads Placeholder] Suchbegriffe: {joined}", platform=platform)]


# B) On-Page & Sitemap ---------------------------------------------------------
class OnpageCollector(SourceCollector):
    id = "onpage"
    label = "On-Page Signale"
    category = "onpage"

    def collect(self) -> List[ContextChunk]:
        url = (self.params.get("url") or "").strip()
        if not url:
            return []
        try:
            sig = extract_seo_signals(url)
            text = json.dumps(sig, indent=2, ensure_ascii=False)
            return [self._chunk(f"onpage:{url}", text)]
        except Exception as e:
            return [self._chunk(f"onpage:{url}", f"[On-Page Fehler: {e}]", type="error")]


class SitemapCollector(SourceCollector):
    id = "sitemap"
    label = "Sitemap.xml"
    category = "sitemap"

    def collect(self) -> List[ContextChunk]:
        import requests  # lazy import
        base_url = (self.params.get("url") or "").strip()
        if not base_url:
            return []
        sm_candidates = [
            base_url.rstrip("/") + "/sitemap.xml",
            base_url.rstrip("/") + "/sitemap_index.xml",
        ]
        out: List[ContextChunk] = []
        for sm in sm_candidates:
            try:
                r = requests.get(sm, timeout=10)
                if r.status_code == 200 and len(r.text) > 50:
                    out.append(self._chunk(f"sitemap:{sm}", r.text))
            except Exception as e:
                out.append(self._chunk(f"sitemap:{sm}", f"[Sitemap Fehler: {e}]", type="error"))
        return out


# D) SERP & Competitors --------------------------------------------------------
class SerpCollector(SourceCollector):
    id = "serp"
    label = "Search Snippets & PAA"
    category = "serp"

    def collect(self) -> List[ContextChunk]:
        provider = self.params.get("provider", "serpapi").lower()
        q = (self.params.get("query") or "").strip()
        if not q:
            return []
        import requests
        chunks: List[ContextChunk] = []
        if provider == "serpapi":
            api_key = os.getenv("SERPAPI_KEY")
            if not api_key:
                return [self._chunk("serp", "[SerpAPI nicht konfiguriert]", provider=provider, type="error")]
            try:
                resp = requests.get(
                    "https://serpapi.com/search.json",
                    params={"engine": "google", "q": q, "hl": "de", "api_key": api_key, "num": 10},
                    timeout=25,
                )
                data = resp.json()
                org = data.get("organic_results", [])[:6]
                lines = []
                for r in org:
                    title = r.get("title")
                    link = r.get("link")
                    snippet = r.get("snippet")
                    lines.append(f"• {title}\n{snippet}\n{link}")
                paa = data.get("related_questions") or data.get("people_also_ask") or []
                if paa:
                    lines.append("\nPeople also ask:")
                    for pq in paa[:6]:
                        qtext = pq.get("question") or pq.get("title")
                        ans = pq.get("snippet") or ""
                        lines.append(f"? {qtext}\n→ {ans}")
                txt = "\n\n".join(lines) or f"[Keine Treffer für {q}]"
                chunks.append(self._chunk(f"serp:serpapi", txt, provider="serpapi", query=q))
            except Exception as e:
                chunks.append(self._chunk("serp:serpapi", f"[SerpAPI Fehler: {e}]", type="error"))
        else:  # bing
            api_key = os.getenv("BING_API_KEY")
            if not api_key:
                return [self._chunk("serp", "[Bing API nicht konfiguriert]", provider=provider, type="error")]
            try:
                headers = {"Ocp-Apim-Subscription-Key": api_key}
                resp = requests.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    params={"q": q, "mkt": "de-DE", "count": 10, "textDecorations": False},
                    headers=headers,
                    timeout=20,
                )
                data = resp.json()
                vals = (data.get("webPages") or {}).get("value", [])[:8]
                lines = [f"Bing Web Search: {q}"]
                for r in vals:
                    lines.append(f"• {r.get('name')}\n{r.get('snippet')}\n{r.get('url')}")
                txt = "\n\n".join(lines)
                chunks.append(self._chunk("serp:bing", txt, provider="bing", query=q))
            except Exception as e:
                chunks.append(self._chunk("serp:bing", f"[Bing API Fehler: {e}]", type="error"))
        return chunks


class CompetitorCollector(SourceCollector):
    id = "competitors"
    label = "Mitbewerber-Kontext"
    category = "competitors"

    def collect(self) -> List[ContextChunk]:
        domains: List[str] = self.params.get("domains") or []
        if not domains:
            return []
        out: List[ContextChunk] = []
        for d in domains[:10]:
            try:
                html = scrape_html(d if d.startswith("http") else f"https://{d}")
                blocks = extract_text_blocks(html)
                text = "\n".join(blocks)[:20000]
                out.append(self._chunk(f"competitor:{d}", text, domain=d))
            except Exception as e:
                out.append(self._chunk(f"competitor:{d}", f"[Fehler beim Laden: {e}]", type="error", domain=d))
        return out


# ---------------------------
# Registry of all collectors (ohne Notion/GDrive)
# ---------------------------
COLLECTOR_REGISTRY = {
    CustomerMemoryCollector.id: CustomerMemoryCollector,
    UrlCollector.id: UrlCollector,
    PdfCollector.id: PdfCollector,
    GuidelinesCollector.id: GuidelinesCollector,
    RssCollector.id: RssCollector,
    TrendsCollector.id: TrendsCollector,
    DestatisCollector.id: DestatisCollector,
    AdsCollector.id: AdsCollector,
    OnpageCollector.id: OnpageCollector,
    SitemapCollector.id: SitemapCollector,
    SerpCollector.id: SerpCollector,
    CompetitorCollector.id: CompetitorCollector,
}


# ---------------------------
# Merger core
# ---------------------------
class ContextMerger:
    def __init__(
        self,
        query: str,
        task: Optional[str] = None,
        url: Optional[str] = None,
        customer_id: Optional[str] = None,
        pdf_path: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        token_budget: int = 6000,
        # which sources to include (after confirmation), with optional per-source params
        selected_sources: Optional[List[str]] = None,
        source_params: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        self.query = (query or "").strip()
        self.task = task
        self.url = url
        self.customer_id = customer_id
        self.pdf_path = pdf_path
        self.fields = fields or {}
        self.token_budget = token_budget
        self.selected_sources = selected_sources or []
        self.source_params = source_params or {}

        self.planned_result: Dict[str, Any] = {}
        self.collected_context: str = ""
        self.provenance: List[Dict[str, Any]] = []

    # -----------------------
    # Phase 1 — Planner (interactive)
    # -----------------------
    def reason_before_merge(self) -> Dict[str, Any]:
        """Erstellt einen Plan und schlägt passende Quellen vor. Holt noch KEINE Daten."""
        suggestions = []
        suggestions += [
            {"id": "customer_memory", "label": CustomerMemoryCollector.label, "default": bool(self.customer_id), "reason": "Kundenwissen & Historie"},
            {"id": "url", "label": UrlCollector.label, "default": bool(self.url), "reason": "Primärquelle Website"},
            {"id": "pdf", "label": PdfCollector.label, "default": bool(self.pdf_path), "reason": "Hinterlegte Doks"},
            {"id": "guidelines", "label": GuidelinesCollector.label, "default": True, "reason": "Qualitätsregeln"},
        ]
        suggestions += [
            {"id": "rss", "label": RssCollector.label, "default": self.task in {"content_writing","content_analysis","campaign_plan","tactical_actions"}, "reason": "Aktuelle Branchensignale"},
            {"id": "trends", "label": TrendsCollector.label, "default": self.task in {"content_writing","campaign_plan"}, "reason": "Suchinteresse & Winkel"},
            {"id": "destatis", "label": DestatisCollector.label, "default": self.task in {"campaign_plan","content_writing","seo_optimization"}, "reason": "Fakten & Größenordnungen"},
            {"id": "ads", "label": AdsCollector.label, "default": self.task in {"competitive_analysis","campaign_plan","landingpage_strategy"}, "reason": "Message-Market Fit & CTAs"},
        ]
        suggestions += [
            {"id": "onpage", "label": OnpageCollector.label, "default": self.task in {"seo_audit","seo_optimization","landingpage_strategy"}, "reason": "Title/Meta/H-Struktur"},
            {"id": "sitemap", "label": SitemapCollector.label, "default": self.task in {"seo_audit","seo_optimization"}, "reason": "Seiteninventar"},
        ]
        suggestions += [
            {"id": "serp", "label": SerpCollector.label, "default": self.task in {"content_writing","seo_optimization","content_analysis"}, "reason": "PAA & SERP-Snippets"},
            {"id": "competitors", "label": CompetitorCollector.label, "default": self.task in {"competitive_analysis","landingpage_strategy"}, "reason": "Wettbewerbsbenchmarks"},
        ]

        planner_prompt = context_merger_planner_prompt.format(
            user_input=self.query,
            task=self.task,
            subtask_prompt="",
            zielgruppe=self.fields.get("zielgruppe", ""),
            thema=self.fields.get("thema", ""),
            tonalitaet=self.fields.get("tonalitaet", ""),
            keyword_fokus=self.fields.get("keyword_fokus", ""),
            plattform=self.fields.get("plattform", ""),
            produktname=self.fields.get("produktname", ""),
            gliederungspunkte=self.fields.get("gliederungspunkte", ""),
            formatwunsch=self.fields.get("formatwunsch", ""),
        )
        try:
            result = llm.invoke(planner_prompt)
            parsed = _safe_json_parse(getattr(result, "content", str(result)))
        except Exception as e:
            parsed = {"error": str(e), "trace": traceback.format_exc()}

        self.planned_result = {
            "plan": parsed,
            "proposed_sources": suggestions,
            "status": "needs_confirmation",
        }
        return self.planned_result

    # -----------------------
    # Phase 2 — Collect & Merge (after user confirmation)
    # -----------------------
    def _instantiate_collectors(self) -> List[SourceCollector]:
        params_base = {
            "customer_id": self.customer_id,
            "url": self.url,
            "pdf_path": self.pdf_path,
        }
        collectors: List[SourceCollector] = []
        chosen = self.selected_sources or [s["id"] for s in (self.planned_result.get("proposed_sources") or []) if s.get("default")]
        for cid in chosen:
            cls = COLLECTOR_REGISTRY.get(cid)
            if not cls:
                continue
            params = {**params_base, **self.fields, **self.source_params.get(cid, {})}
            try:
                collectors.append(cls(**params))
            except Exception:
                pass
        return collectors

    def _score_chunks(self, chunks: List[ContextChunk]) -> List[ContextChunk]:
        kws: List[str] = []
        kws.extend(re.findall(r"[\wäöüÄÖÜß-]{3,}", self.query))
        for k in ("zielgruppe", "thema", "keyword_fokus", "produktname", "plattform"):
            v = self.fields.get(k, "")
            if isinstance(v, str):
                kws.extend(re.findall(r"[\wäöüÄÖÜß-]{3,}", v))
        kws = [k.lower() for k in kws if k]

        for ch in chunks:
            kw_score = _keyword_score(ch.content or "", kws)
            len_penalty = min(1.0, 20000 / max(1, len(ch.content or "")))
            cat_w = CATEGORY_WEIGHTS.get((ch.meta or {}).get("category", ""), 0.5)
            ch.score = (0.6 * kw_score + 0.4 * len_penalty) * (0.6 + 0.4 * cat_w)
        return chunks

    def _select_and_merge(self, chunks: List[ContextChunk]) -> Tuple[str, List[ContextChunk]]:
        chunks = _dedup_chunks(chunks)
        chunks = self._score_chunks(chunks)
        chunks.sort(key=lambda c: c.score, reverse=True)
        merged_parts: List[str] = []
        selected: List[ContextChunk] = []
        for ch in chunks:
            candidate = f"\n\n--- source:{ch.source} [{(ch.meta or {}).get('category','')}] ---\n\n" + (ch.content or "")
            if _token_estimate("\n".join(merged_parts) + candidate) > self.token_budget:
                continue
            merged_parts.append(candidate)
            selected.append(ch)
        if not merged_parts and chunks:
            top = chunks[0]
            selected = [top]
            merged_parts = [top.content[: min(len(top.content), 16000)]]
        return "\n\n".join(merged_parts).strip(), selected

    def collect_context_after_confirmation(self, selected_sources: Optional[List[str]] = None, source_params: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        if selected_sources is not None:
            self.selected_sources = selected_sources
        if source_params is not None:
            self.source_params = source_params
        try:
            collectors = self._instantiate_collectors()
            chunks: List[ContextChunk] = []
            for c in collectors:
                chunks.extend(c.collect())
            merged, selected = self._select_and_merge(chunks)
            self.collected_context = merged
            self.provenance = [s.to_dict() for s in selected]
            return {"merged_context": merged or "[Kein Kontext verfügbar]", "provenance": self.provenance}
        except Exception as e:
            return {"merged_context": f"[Fehler bei der Kontextsammlung: {e}]"}

    # -----------------------
    # Phase 3 — Finalize bundle for subtask
    # -----------------------
    def get_final_context_bundle(self) -> Dict[str, Any]:
        prompt = context_merger_executor_prompt.format(
            user_input=self.query,
            task=self.task,
            subtask_prompt="",
            merged_context=_truncate_to_token_budget(self.collected_context, int(self.token_budget * 0.9)),
        )
        try:
            result = llm.invoke(prompt)
            parsed = _safe_json_parse(getattr(result, "content", str(result)))
            bundle = {
                "merged_context": parsed.get("final_context_summary") or parsed.get("merged_context") or self.collected_context or "",
                "fields": parsed.get("field_suggestions", {}),
                "task": self.task,
                "status": parsed.get("status", "finalized"),
                "provenance": self.provenance,
                "selected_sources": self.selected_sources,
            }
            if not bundle["merged_context"]:
                bundle["merged_context"] = _truncate_to_token_budget(self.collected_context, self.token_budget)
            return bundle
        except Exception as e:
            return {"error": str(e), "trace": traceback.format_exc(), "status": "finalization_failed", "provenance": self.provenance, "selected_sources": self.selected_sources}
