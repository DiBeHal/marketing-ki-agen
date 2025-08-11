"""
agent/base_agent.py — v4 (Context-Merger–first)

Kernausrichtung:
- Orchestrator übergibt NUR noch kontextuelle Felder (vom Context Merger) an die Task-Prompts
- KEIN eigenes Scraping von RSS/Trends/DESTATIS/Ads mehr hier drinnen
- Lighthouse bleibt als einziges externes technisches Tool in diesem Modul
- Einheitliche Task-Namen (seo_optimization als kanonischer Name; Alias: seo_optimize)
- Kein Deep/Standard-Modus mehr – Parameter wird toleriert, aber nicht verwendet
- Optionales Speichern ins Memory nach erfolgreichem Lauf (save_to_memory=True)

Voraussetzungen:
- prompts.py liefert die *…_prompt_deep*-Vorlagen
- loader.py liefert load_pdf, load_html (eigener Reader), extract_seo_signals
- tools.lighthouse_runner liefert run_lighthouse(url)
- context_utils.get_context_from_text_or_url vereinigt Text, URL, PDF & Kundengedächtnis

Rückgabeformat:
{
  "response": str,
  "questions": List[str],        # falls Clarifier verfügbar
  "prompt_used": str,            # zur Nachvollziehbarkeit
  "conversation_id": Optional[str]
}
"""
from __future__ import annotations

import os
import uuid
import json
from typing import Any, Dict, Optional, List

# --- Fallback-freundliche Imports (Repo-Struktur variiert lokal/Cloud) ---
try:
    from agent.prompts import (
        content_analysis_prompt_deep,
        content_write_prompt_deep,
        competitive_analysis_prompt_deep,
        campaign_plan_prompt_deep,
        landingpage_strategy_contextual_prompt_deep,
        seo_audit_prompt_deep,
        seo_optimization_prompt_deep,
        seo_lighthouse_prompt_deep,
        tactical_actions_prompt_deep,
        alt_tag_writer_prompt_deep,
        extract_topics_prompt_deep,
    )
except Exception:  # pragma: no cover
    from prompts import (
        content_analysis_prompt_deep,
        content_write_prompt_deep,
        competitive_analysis_prompt_deep,
        campaign_plan_prompt_deep,
        landingpage_strategy_contextual_prompt_deep,
        seo_audit_prompt_deep,
        seo_optimization_prompt_deep,
        seo_lighthouse_prompt_deep,
        tactical_actions_prompt_deep,
        alt_tag_writer_prompt_deep,
        extract_topics_prompt_deep,
    )

try:
    from agent.context_utils import get_context_from_text_or_url
except Exception:  # pragma: no cover
    try:
        from agent.tools.context_utils import get_context_from_text_or_url
    except Exception:
        from context_utils import get_context_from_text_or_url

try:
    from agent.loader import load_pdf, load_html as loader_load_html, extract_seo_signals
except Exception:  # pragma: no cover
    from loader import load_pdf, load_html as loader_load_html, extract_seo_signals

try:
    from agent.tools.scraper import scrape_html
    from agent.tools.parser import extract_text_blocks
except Exception:  # pragma: no cover
    scrape_html = None
    extract_text_blocks = None

try:
    from agent.tools.alt_tag_helper import extract_images_from_url
except Exception:  # pragma: no cover
    extract_images_from_url = None

try:
    from agent.tools.lighthouse_runner import run_lighthouse
except Exception:  # pragma: no cover
    run_lighthouse = None

try:
    from agent.customer_memory import save_customer_memory
except Exception:  # pragma: no cover
    from customer_memory import save_customer_memory

try:
    from agent.activity_log import log_event
except Exception:  # pragma: no cover
    def log_event(payload: Dict[str, Any]):
        pass

# Clarifier ist optional
try:  # pragma: no cover
    from agent.clarifier import extract_questions_from_response, merge_clarifications
except Exception:  # pragma: no cover
    extract_questions_from_response = None
    merge_clarifications = None

try:
    from langchain_openai import ChatOpenAI
except Exception:  # pragma: no cover
    ChatOpenAI = None


# =======================
# Anforderungen pro Task
# =======================
TASK_REQUIREMENTS: Dict[str, Dict[str, str]] = {
    "seo_audit": {"url": "required"},
    "seo_optimization": {"text|url|customer_id": "any_of"},  # alias: seo_optimize
    "seo_lighthouse": {"urls": "required"},
    "content_analysis": {"text|url|customer_id": "any_of"},
    "content_writing": {"zielgruppe": "required", "tonalitaet": "required", "thema": "required"},
    "campaign_plan": {"text|url|customer_id": "any_of", "zielgruppe": "required", "thema": "required"},
    "landingpage_strategy": {"url": "required"},
    "tactical_actions": {"text|url|customer_id": "any_of"},
    "alt_tag_writer": {"url": "required"},
    "extract_topics": {"text": "required"},
    # Zusätzlich vorhanden in UI/Prompts
    "competitive_analysis": {"text|url|customer_id": "any_of"},
}


def _has_any(*vals: Any) -> bool:
    return any(v is not None and str(v).strip() for v in vals)


def _check_requirements(task: str, kwargs: Dict[str, Any]) -> None:
    req = TASK_REQUIREMENTS.get(task, {})
    for key, rule in req.items():
        if rule == "required" and not kwargs.get(key):
            raise ValueError(f"Task '{task}' benötigt zwingend: {key}")
        if rule == "any_of":
            if not _has_any(*[kwargs.get(k) for k in key.split("|")]):
                raise ValueError(f"Task '{task}' benötigt mindestens einen dieser Werte: {key}")


# Single LLM-Client (keine Deep/Standard-Unterscheidung mehr)
_llm = ChatOpenAI(model="gpt-4o", max_tokens=3000) if ChatOpenAI else None


def _safe_questions(text: str) -> List[str]:
    if extract_questions_from_response:
        try:
            return extract_questions_from_response(text)
        except Exception:
            return []
    return []


def _maybe_merge_clarifications(prompt: str, clarifications: Optional[Dict[str, Any]]) -> str:
    if merge_clarifications and clarifications:
        try:
            return merge_clarifications(prompt, clarifications)
        except Exception:
            return prompt
    return prompt


# =======================
# Hauptschnittstelle
# =======================

def run_agent(
    task: str,
    *,
    conversation_id: Optional[str] = None,
    clarifications: Optional[Dict[str, Any]] = None,
    save_to_memory: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Führt einen Marketing-Subtask anhand der Prompts aus.

    Wichtige Design-Entscheidung: Alle externen Daten (RSS, Trends, DESTATIS, Ads,
    zusätzliche HTML-Kontexte etc.) sollen vom Context Merger geladen & hier nur als Felder
    (z. B. rss_snippets, trends_insights, destatis_stats, google_ads …) übergeben werden.
    """
    if not conversation_id:
        conversation_id = str(uuid.uuid4())

    # Alias-Gleichzug
    if task == "seo_optimize":
        task = "seo_optimization"

    # Anforderungen prüfen
    _check_requirements(task, kwargs)

    # Hilfs-Kontext (nur falls nötig) – bevorzugt: bereits gemergter Kontext via kwargs["text"]
    def _ctx_from_inputs() -> str:
        return get_context_from_text_or_url(
            kwargs.get("text", ""),
            kwargs.get("url", ""),
            kwargs.get("customer_id"),
            kwargs.get("pdf_path"),
        )

    prompt = None
    response_text = None

    # ---------------
    # Routing
    # ---------------
    if task == "content_analysis":
        ctx = kwargs.get("text") or _ctx_from_inputs()
        prompt = content_analysis_prompt_deep.format(
            context=ctx,
            rss_snippets=kwargs.get("rss_snippets", ""),
            trends_insights=kwargs.get("trends_insights", ""),
            destatis_stats=kwargs.get("destatis_stats", ""),
        )

    elif task == "content_writing":
        ctx = kwargs.get("text") or _ctx_from_inputs()
        prompt = content_write_prompt_deep.format(
            zielgruppe=kwargs.get("zielgruppe", ""),
            tonalitaet=kwargs.get("tonalitaet", ""),
            thema=kwargs.get("thema", ""),
            format_laenge=kwargs.get("format_laenge", "Artikel ca. 600 Wörter"),
            context=ctx,
            rss_snippets=kwargs.get("rss_snippets", ""),
            trends_insights=kwargs.get("trends_insights", ""),
            destatis_stats=kwargs.get("destatis_stats", ""),
        )

    elif task == "campaign_plan":
        ctx = kwargs.get("text") or _ctx_from_inputs()
        prompt = campaign_plan_prompt_deep.format(
            context=ctx,
            zielgruppe=kwargs.get("zielgruppe", ""),
            thema=kwargs.get("thema", ""),
            ziel=kwargs.get("ziel", "Nicht angegeben"),
            produkt=kwargs.get("produkt", ""),
            zeitraum=kwargs.get("zeitraum", ""),
            rss_snippets=kwargs.get("rss_snippets", ""),
            trends_insights=kwargs.get("trends_insights", ""),
            destatis_stats=kwargs.get("destatis_stats", ""),
        )

    elif task == "tactical_actions":
        ctx = kwargs.get("text") or _ctx_from_inputs()
        # Topic-Keywords können vom Merger kommen – ansonsten optional leer
        topic_keywords = kwargs.get("topic_keywords")
        if isinstance(topic_keywords, list):
            topic_keywords = ", ".join([t for t in topic_keywords if t])
        prompt = tactical_actions_prompt_deep.format(
            context=ctx,
            ziel=kwargs.get("ziel", ""),
            zeitfenster=kwargs.get("zeitfenster", ""),
            rss_snippets=kwargs.get("rss_snippets", ""),
            trends_insights=kwargs.get("trends_insights", ""),
            destatis_stats=kwargs.get("destatis_stats", ""),
            keywords=topic_keywords or "",
            seo_summary=kwargs.get("seo_summary", ""),
        )

    elif task == "landingpage_strategy":
        # Diese Task benötigt realen Seiten-Text → einfache HTML-Extraktion, falls nicht bereits vorhanden
        ctx_website = ""
        url = kwargs.get("url", "").strip()
        if url and scrape_html and extract_text_blocks:
            try:
                html = scrape_html(url)
                ctx_website = "\n".join(extract_text_blocks(html))
            except Exception as e:
                ctx_website = f"[Fehler beim Laden/Parsen: {e}]"
        else:
            # Fallback: Leser aus loader.py
            try:
                ctx_website = loader_load_html(url)
            except Exception as e:
                ctx_website = f"[Fehler beim Laden/Parsen: {e}]"

        base_ctx = kwargs.get("text") or _ctx_from_inputs()
        prompt = landingpage_strategy_contextual_prompt_deep.format(
            context=base_ctx,
            context_website=ctx_website,
            zielgruppe=kwargs.get("zielgruppe", ""),
            ziel=kwargs.get("ziel", ""),
            thema=kwargs.get("angebot", ""),
            rss_snippets=kwargs.get("rss_snippets", ""),
            trends_insights=kwargs.get("trends_insights", ""),
            destatis_stats=kwargs.get("destatis_stats", ""),
            google_ads=kwargs.get("google_ads", ""),
            facebook_ads=kwargs.get("facebook_ads", ""),
            linkedin_ads=kwargs.get("linkedin_ads", ""),
        )

    elif task == "alt_tag_writer":
        url = kwargs.get("url", "").strip()
        branche = kwargs.get("branche", "Allgemein")
        zielgruppe = kwargs.get("zielgruppe", "Kunden")
        text_for_context = kwargs.get("text", "") or _ctx_from_inputs()
        image_context = "[Kein Bild-Scraper verfügbar]"
        if extract_images_from_url and url:
            try:
                images = extract_images_from_url(url)
                if isinstance(images, list) and images:
                    lines = []
                    for i, img in enumerate(images[:40], 1):
                        src = img.get("src") or img.get("url") or ""
                        ctx = img.get("context", "")
                        if src:
                            lines.append(f"Bild {i}: {src}")
                            if ctx:
                                lines.append(f"Kontext: {ctx}")
                    image_context = "\n".join(lines)
            except Exception as e:
                image_context = f"[Fehler beim Laden der Bilder: {e}]"
        prompt = alt_tag_writer_prompt_deep.format(
            url=url,
            branche=branche,
            zielgruppe=zielgruppe,
            text=text_for_context,
            image_context=image_context,
        )

    elif task == "extract_topics":
        text = (kwargs.get("text") or "").strip()
        if not text:
            text = _ctx_from_inputs().strip()
        if not text:
            raise ValueError("❗ Kein Text übergeben für Topic-Extraktion.")
        prompt = extract_topics_prompt_deep.format(text=text)

    elif task == "seo_audit":
        ctx = kwargs.get("text") or _ctx_from_inputs()
        url = kwargs.get("url", "")
        zielgruppe = kwargs.get("zielgruppe", "")
        thema = kwargs.get("thema", "")
        keywords = kwargs.get("topic_keywords", [])
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)
        # Leichte Onpage-Signale zur Kontextanreicherung (keine externen Quellen)
        title = meta_description = ""
        headings = ""
        num_links = cta_links = 0
        try:
            sig = extract_seo_signals(url)
            title = sig.get("title", "")
            meta_description = sig.get("meta_description", "")
            headings = "\n".join(sig.get("headings", [])[:10])
            num_links = sig.get("num_links", 0)
            cta_links = sig.get("cta_links", 0)
        except Exception:
            pass
        prompt = seo_audit_prompt_deep.format(
            contexts_combined=ctx,
            zielgruppe=zielgruppe,
            thema=thema,
            keywords=keywords,
            title=title,
            meta_description=meta_description,
            headings=headings,
            num_links=num_links,
            cta_links=cta_links,
            rss_snippets=kwargs.get("rss_snippets", ""),
            trends_insights=kwargs.get("trends_insights", ""),
            destatis_stats=kwargs.get("destatis_stats", ""),
        )

    elif task == "seo_optimization":  # alias oben abgefangen
        ctx = kwargs.get("text") or _ctx_from_inputs()
        prompt = seo_optimization_prompt_deep.format(
            contexts_combined=ctx,
            focus_url=kwargs.get("url", ""),
            seo_audit_summary=kwargs.get("seo_audit_summary", ""),
            lighthouse_json=kwargs.get("lighthouse_json", ""),
            zielgruppe=kwargs.get("zielgruppe", ""),
            ziel=kwargs.get("ziel", ""),
            thema=kwargs.get("thema", ""),
            rss_snippets=kwargs.get("rss_snippets", ""),
            trends_insights=kwargs.get("trends_insights", ""),
            destatis_stats=kwargs.get("destatis_stats", ""),
        )

    elif task == "seo_lighthouse":
        if run_lighthouse is None:
            raise RuntimeError("Lighthouse-Runner nicht verfügbar")
        urls: List[str] = kwargs.get("urls", []) or []
        if not urls:
            raise ValueError("❗ Bitte mindestens eine URL angeben.")
        base_ctx = kwargs.get("text") or _ctx_from_inputs()
        analyses = []
        last_lh_json = ""
        for u in urls:
            # pro URL: (leichter) Seitentext + Lighthouse-Kern
            ctx_u = base_ctx
            try:
                lh_raw = run_lighthouse(u)
                last_lh_json = json.dumps(lh_raw.get("categories", {}).get("seo", {}), indent=2) if isinstance(lh_raw, dict) else str(lh_raw)
            except Exception as e:
                last_lh_json = f"[Fehler bei Lighthouse: {e}]"
            analyses.append(f"""=== {u} ===\n\nWebsite-Kontext:\n{ctx_u}\n\nLighthouse-Report:\n{last_lh_json}""")
        combined_input = "\n\n".join(analyses)
        prompt = seo_lighthouse_prompt_deep.format(
            context=base_ctx,
            context_website=combined_input,
            branche=kwargs.get("branche", ""),
            zielgruppe=kwargs.get("zielgruppe", ""),
            thema=kwargs.get("thema", ""),
            url="Mehrere URLs",
            lighthouse_reports_combined=last_lh_json,
        )

    elif task == "competitive_analysis":
        # Alles, was an Wettbewerbs-/Ads-Infos gebraucht wird, soll vom Merger angeliefert werden
        ctx_customer = kwargs.get("text") or _ctx_from_inputs()
        # Optional können hier bereits zusammengeführte Wettbewerbs-Kontexte übergeben werden
        competitors_context = kwargs.get("competitors_context", "")
        prompt = competitive_analysis_prompt_deep.format(
            kunde_name=kwargs.get("customer_name", "Unsere Firma"),
            branche=kwargs.get("branche", "Allgemein"),
            zielgruppe=kwargs.get("zielgruppe", "Kunden"),
            contexts_combined_kunde=ctx_customer,
            contexts_combined_mitbewerber=competitors_context,
            google_ads=kwargs.get("google_ads", ""),
            facebook_ads=kwargs.get("facebook_ads", ""),
            linkedin_ads=kwargs.get("linkedin_ads", ""),
        )

    elif task == "memory_write":
        content = (kwargs.get("text") or "").strip()
        customer_id = (kwargs.get("customer_id") or "").strip()
        if not content:
            raise ValueError("Kein Inhalt zum Speichern übergeben.")
        if not customer_id:
            raise ValueError("Kein Kunden-ID vorhanden.")
        save_customer_memory(customer_id, content)
        return {"response": f"🧠 Kontext gespeichert für Kunde {customer_id}.", "questions": [], "prompt_used": "", "conversation_id": conversation_id}

    elif task == "memory_search":
        # Einfache Volltextsuche (Fallback, wenn vektorbasierte Suche nicht vorhanden)
        query = (kwargs.get("query") or "").strip().lower()
        if not query:
            raise ValueError("Kein Suchbegriff übergeben.")
        folder = os.path.join(os.getcwd(), "customer_memory")
        matches: List[str] = []
        if os.path.isdir(folder):
            for fn in os.listdir(folder):
                if not fn.endswith(".json"):
                    continue
                try:
                    data = json.load(open(os.path.join(folder, fn), "r"))
                    for item in data:
                        content = item.get("content", "")
                        if query in content.lower():
                            matches.append(content)
                except Exception:
                    continue
        return {"response": "\n\n".join(matches) if matches else "❌ Keine passenden Inhalte im Memory gefunden.", "questions": [], "prompt_used": "", "conversation_id": conversation_id}

    else:
        raise ValueError(f"Unbekannter Task: {task}")

    # Klarstellungen in Prompt einfügen (optional)
    prompt = _maybe_merge_clarifications(prompt, clarifications)

    # --- LLM Call ---
    if _llm is None:
        raise RuntimeError("LLM-Client nicht initialisiert (langchain_openai fehlt)")
    resp = _llm.invoke(prompt)
    response_text = resp.content if hasattr(resp, "content") else str(resp)

    # Folgefragen extrahieren (optional)
    questions = _safe_questions(response_text)

    # Optional: Ergebnis ins Memory drücken
    if save_to_memory and kwargs.get("customer_id"):
        try:
            save_customer_memory(kwargs["customer_id"], response_text)
        except Exception:
            pass

    # Logging (leichtgewichtig)
    try:
        log_event({"type": "task_run", "task": task, "customer_id": kwargs.get("customer_id"), "conversation_id": conversation_id})
    except Exception:
        pass

    return {
        "response": response_text,
        "questions": questions,
        "prompt_used": prompt,
        "conversation_id": conversation_id,
    }
