# agent/base_agent.py

import os
import uuid
import json
from typing import Any, Dict, Optional, List
from urllib.parse import urlparse

import feedparser
import requests
from pytrends.request import TrendReq
from langchain_openai import ChatOpenAI

from agent.prompts import (
    content_analysis_prompt_fast, content_analysis_prompt_deep,
    content_write_prompt_fast, content_write_prompt_deep,
    competitive_analysis_prompt_fast, competitive_analysis_prompt_deep,
    campaign_plan_prompt_fast, campaign_plan_prompt_deep,
    landingpage_strategy_contextual_prompt_fast, landingpage_strategy_contextual_prompt_deep,
    seo_audit_prompt_fast, seo_audit_prompt_deep,
    seo_optimization_prompt_fast, seo_optimization_prompt_deep,
    seo_lighthouse_prompt_fast, seo_lighthouse_prompt_deep,
    monthly_report_prompt_fast, monthly_report_prompt_deep,
    tactical_actions_prompt_fast, tactical_actions_prompt_deep
)
from agent.clarifier import extract_questions_from_response, merge_clarifications
from agent.tools.lighthouse_runner import run_lighthouse
from agent.loader import load_html, extract_seo_signals, load_pdf
from agent.customer_memory import load_customer_memory
from agent.activity_log import log_event
from agent.tools.ads_runner import (
    fetch_linkedin_ads, fetch_google_ads, fetch_facebook_ads
)

# ===== LangChain LLM mit Token-Limit =====
llm = ChatOpenAI(model="gpt-4o", max_tokens=3000)


def search_google(brand_or_domain: str) -> List[str]:
    parsed = urlparse(brand_or_domain)
    host = parsed.netloc or brand_or_domain
    if host.startswith("www."):
        host = host[4:]
    brand = host.split(".")[0]
    return [
        f"https://www.linkedin.com/company/{brand}",
        f"https://news.google.com/search?q={brand}"
    ]


def get_context_from_text_or_url(
    text: str,
    url: str,
    customer_id: Optional[str] = None
) -> str:
    """
    Lädt Kontext aus Kunden-Memory, reinem Text oder einer URL.
    """
    context = ""
    if customer_id:
        context += load_customer_memory(customer_id) + "\n\n"
    if text and len(text.strip().split()) > 50:
        context += text.strip()
    if url:
        try:
            context += "\n" + load_html(url)
        except Exception as e:
            context += f"\n[Fehler beim Laden von {url}: {e}]"
    if not context.strip():
        raise ValueError("Kein verwertbarer Inhalt vorhanden (Text, URL oder Kunden-Memory).")
    return context


# ===== Helper für externe Datenquellen =====

def fetch_rss_snippets(feeds: List[str], limit: int = 3) -> str:
    snippets = []
    for feed in feeds:
        try:
            d = feedparser.parse(feed)
            for entry in d.entries[:limit]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                snippets.append(f"- {title} ({link})")
        except Exception:
            continue
    return "\n".join(snippets)


def fetch_trends_insights(
    keywords: List[str],
    timeframe: str = "now 7-d"
) -> str:
    if not keywords:
        return ""
    try:
        pytrends = TrendReq()
        pytrends.build_payload(keywords, timeframe=timeframe)
        df = pytrends.interest_over_time()
        insights = []
        for kw in keywords:
            if kw in df.columns:
                series = df[kw].dropna()
                if not series.empty:
                    change = series.iloc[-1] - series.iloc[0]
                    insights.append(f"- Suchinteresse für '{kw}' im Zeitraum: Änderung um {change} Punkte")
        return "\n".join(insights)
    except Exception:
        return ""


def fetch_destatis_stats(codes: List[str]) -> str:
    stats = []
    for code in codes:
        try:
            url = f"https://api.destatis.de/v1/statistics/{code}"
            res = requests.get(url, timeout=5)
            if res.ok:
                data = res.json()
                # Annahme: 'value' Feld enthält die relevante Kennzahl
                value = data.get("value", "n/a")
                stats.append(f"- {code}: {value}")
        except Exception:
            continue
    return "\n".join(stats)


# ===== Haupt-Dispatcher =====

def run_agent(
    task: str,
    reasoning_mode: str = "fast",
    conversation_id: Optional[str] = None,
    clarifications: Optional[Dict[str, str]] = None,
    **kwargs: Any
) -> Dict[str, Any]:
    # 1) Session-ID erzeugen, falls nicht vorhanden
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    # 2) Externe Daten nur im Deep-Modus vorladen
    rss_snippets = trends_insights = destatis_stats = ""
    google_ads = facebook_ads = linkedin_ads = ""
    if reasoning_mode == "deep":
        rss_snippets = fetch_rss_snippets(kwargs.get("rss_feeds", []))
        trends_insights = fetch_trends_insights(kwargs.get("trend_keywords", []))
        destatis_stats = fetch_destatis_stats(kwargs.get("destatis_queries", []))
        if task in ("vergleich", "landingpage_strategy"):
            linkedin_ads = fetch_linkedin_ads(kwargs.get("linkedin_company", ""), limit=3)
            google_ads = fetch_google_ads(kwargs.get("google_company", ""), limit=3)
            facebook_ads = fetch_facebook_ads(kwargs.get("facebook_page", ""), limit=3)

    # 3) Prompt-Auswahl und -Bau pro Task
    if task == "content_analysis":
        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id")
        )
        tmpl = content_analysis_prompt_fast if reasoning_mode == "fast" else content_analysis_prompt_deep
        if reasoning_mode == "fast":
            prompt = tmpl.format(context=ctx)
        else:
            prompt = tmpl.format(
                context=ctx,
                rss_snippets=rss_snippets,
                trends_insights=trends_insights,
                destatis_stats=destatis_stats
            )

    elif task == "briefing_write":
        zg = kwargs.get("zielgruppe")
        ton = kwargs.get("tonalitaet")
        th = kwargs.get("thema")
        if not all([zg, ton, th]):
            raise ValueError("Zielgruppe, Tonalität und Thema sind Pflichtfelder.")
        tmpl = content_write_prompt_fast if reasoning_mode == "fast" else content_write_prompt_deep
        prompt = tmpl.format(
            zielgruppe=zg,
            tonalitaet=ton,
            thema=th,
            rss_snippets=rss_snippets,
            trends_insights=trends_insights,
            destatis_stats=destatis_stats
        )

    elif task == "vergleich":
        # Multi-URL Wettbewerbsanalyse
        if kwargs.get("eigene_url") and kwargs.get("wettbewerber_urls"):
            ctx_k = load_html(kwargs["eigene_url"])
            results = []
            for url in kwargs["wettbewerber_urls"]:
                try:
                    ctx_m = load_html(url.strip())
                    for link in search_google(url.strip()):
                        ctx_m += "\n" + load_html(link)
                    tmpl = (competitive_analysis_prompt_fast
                            if reasoning_mode == "fast"
                            else competitive_analysis_prompt_deep)
                    if reasoning_mode == "fast":
                        prompt = tmpl.format(
                            context_kunde=ctx_k,
                            context_mitbewerber=ctx_m
                        )
                    else:
                        prompt = tmpl.format(
                            context_kunde=ctx_k,
                            context_mitbewerber=ctx_m,
                            rss_snippets=rss_snippets,
                            trends_insights=trends_insights,
                            google_ads=google_ads,
                            facebook_ads=facebook_ads,
                            linkedin_ads=linkedin_ads
                        )
                    resp = llm.invoke(prompt)
                    content = resp.content
                    if hasattr(resp, "usage"):
                        log_event({
                            "type": "usage",
                            "customer_id": kwargs.get("customer_id"),
                            "conversation_id": conversation_id,
                            "task": task,
                            "mode": reasoning_mode,
                            "input_tokens": resp.usage.prompt_tokens,
                            "output_tokens": resp.usage.completion_tokens
                        })
                    results.append(f"🔗 {url}\n{content}")
                except Exception as e:
                    results.append(f"❌ Fehler bei {url}: {e}")
            aggregated = "\n\n---\n\n".join(results)
            log_event({
                "type": "task_run",
                "customer_id": kwargs.get("customer_id"),
                "task": task,
                "mode": reasoning_mode
            })
            return {"response": aggregated, "questions": [], "conversation_id": conversation_id}

        # Einfache Text-gegen-Text-Vergleich
        ck = kwargs.get("text_kunde")
        cm = kwargs.get("text_mitbewerber")
        if not ck or not cm:
            raise ValueError("Beide Texte (Kunde & Mitbewerber) werden benötigt")
        tmpl = (competitive_analysis_prompt_fast
                if reasoning_mode == "fast"
                else competitive_analysis_prompt_deep)
        if reasoning_mode == "fast":
            prompt = tmpl.format(
                context_kunde=ck,
                context_mitbewerber=cm
            )
        else:
            prompt = tmpl.format(
                context_kunde=ck,
                context_mitbewerber=cm,
                rss_snippets=rss_snippets,
                trends_insights=trends_insights,
                google_ads=google_ads,
                facebook_ads=facebook_ads,
                linkedin_ads=linkedin_ads
            )

    elif task == "seo_audit":
        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id")
        )
        signals = extract_seo_signals(kwargs.get("url", ""))
        raw_lh = run_lighthouse(kwargs.get("url", ""))
        if isinstance(raw_lh, dict):
            seo_score = raw_lh.get("categories", {}).get("seo", {})
        else:
            seo_score = {}
        combined = (
            f"TEXT-INHALT:\n{ctx}\n\n"
            f"TECHNIK:\n{json.dumps(signals, indent=2)}\n\n"
            f"LIGHTHOUSE:\n"
            f"{json.dumps(seo_score, indent=2) if seo_score else '(Keine Lighthouse-Daten verfügbar)'}"
        )
        tmpl = seo_audit_prompt_fast if reasoning_mode == "fast" else seo_audit_prompt_deep
        prompt = tmpl.format(context=combined)

    elif task == "seo_optimize":
        txt = kwargs.get("text", "")
        url = kwargs.get("url", "")
        audit_pdf = kwargs.get("audit_pdf_path")
        full = get_context_from_text_or_url(txt, url, kwargs.get("customer_id"))
        if url:
            full += "\n\nWebsite-Text:\n" + load_html(url)
            full += "\n\nSEO-Signale:\n" + json.dumps(extract_seo_signals(url), indent=2)
        if audit_pdf and os.path.exists(audit_pdf):
            full += "\n\nSEO Audit Report:\n" + load_pdf(audit_pdf)
        tmpl = (seo_optimization_prompt_fast
                if reasoning_mode == "fast"
                else seo_optimization_prompt_deep)
        prompt = tmpl.format(context=full)

    elif task == "campaign_plan":
        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id")
        )
        tmpl = (campaign_plan_prompt_fast
                if reasoning_mode == "fast"
                else campaign_plan_prompt_deep)
        if reasoning_mode == "fast":
            prompt = tmpl.format(context=ctx)
        else:
            prompt = tmpl.format(
                context=ctx,
                rss_snippets=rss_snippets,
                trends_insights=trends_insights,
                destatis_stats=destatis_stats
            )

    elif task == "seo_lighthouse":
        url = kwargs.get("url", "")
        if not url:
            raise ValueError("URL für Lighthouse-Analyse fehlt.")
        raw_lh = run_lighthouse(url)
        if isinstance(raw_lh, dict):
            seo_data = raw_lh.get("categories", {}).get("seo", {})
        else:
            seo_data = {}
        seo_data_str = json.dumps(seo_data, indent=2) if seo_data else "(Keine Lighthouse-Daten verfügbar)"
        tmpl = (seo_lighthouse_prompt_fast
                if reasoning_mode == "fast"
                else seo_lighthouse_prompt_deep)
        prompt = tmpl.format(context=seo_data_str)

    elif task == "landingpage_strategy":
        url = kwargs.get("url", "")
        if not url:
            raise ValueError("URL für Landingpage-Strategie fehlt.")
        ctx_web = load_html(url)
        ctx_att = ""
        pdfp = kwargs.get("pdf_path", "")
        if pdfp and os.path.exists(pdfp):
            ctx_att = load_pdf(pdfp)
        tmpl = (landingpage_strategy_contextual_prompt_fast
                if reasoning_mode == "fast"
                else landingpage_strategy_contextual_prompt_deep)
        if reasoning_mode == "fast":
            prompt = tmpl.format(
                context_website=ctx_web,
                context_anhang=ctx_att
            )
        else:
            prompt = tmpl.format(
                context_website=ctx_web,
                context_anhang=ctx_att,
                rss_snippets=rss_snippets,
                trends_insights=trends_insights,
                destatis_stats=destatis_stats,
                google_ads=google_ads,
                facebook_ads=facebook_ads,
                linkedin_ads=linkedin_ads
            )

    elif task == "monthly_report":
        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id")
        )
        pdfp = kwargs.get("audit_pdf_path")
        if pdfp and os.path.exists(pdfp):
            ctx += "\n\nPDF Anhang:\n" + load_pdf(pdfp)
        tmpl = (monthly_report_prompt_fast
                if reasoning_mode == "fast"
                else monthly_report_prompt_deep)
        prompt = tmpl.format(context=ctx)

    elif task == "tactical_actions":
        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id")
        )
        pdfp = kwargs.get("audit_pdf_path")
        if pdfp and os.path.exists(pdfp):
            ctx += "\n\n[Ergänzende Analyse aus PDF]:\n" + load_pdf(pdfp)
        tmpl = (tactical_actions_prompt_fast
                if reasoning_mode == "fast"
                else tactical_actions_prompt_deep)
        prompt = tmpl.format(context=ctx)

    else:
        raise ValueError(f"Unbekannter Task: {task}")

    # 4) Deep-Loop: Klarstellungen mergen
    if reasoning_mode == "deep" and clarifications:
        prompt = merge_clarifications(prompt, clarifications)

    # 5) LLM-Aufruf
    resp = llm.invoke(prompt)
    content = resp.content if hasattr(resp, "content") else str(resp)

    # 6) Usage-Logging nur wenn verfügbar
    if hasattr(resp, "usage"):
        log_event({
            "type": "usage",
            "customer_id": kwargs.get("customer_id"),
            "conversation_id": conversation_id,
            "task": task,
            "mode": reasoning_mode,
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens
        })

    # 7) Rückfragen extrahieren (nur deep)
    questions = extract_questions_from_response(content) if reasoning_mode == "deep" else []

    # 8) Task-Run-Logging
    log_event({
        "type": "task_run",
        "customer_id": kwargs.get("customer_id"),
        "task": task,
        "mode": reasoning_mode
    })

    return {
        "response": content,
        "questions": questions,
        "conversation_id": conversation_id
    }
