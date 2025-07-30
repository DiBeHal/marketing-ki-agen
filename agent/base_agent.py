# agent/base_agent.py
from agent.services.trends import fetch_trends_insights
from agent.services.rss import fetch_rss_snippets
from agent.services.destatis import fetch_destatis_stats

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

from agent.prompts import (
    alt_tag_writer_prompt_fast, alt_tag_writer_prompt_deep
)

from agent.clarifier import extract_questions_from_response, merge_clarifications
from agent.tools.lighthouse_runner import run_lighthouse
from agent.loader import load_html, extract_seo_signals, load_pdf
from agent.customer_memory import load_customer_memory
from agent.activity_log import log_event
from agent.tools.ads_scraper import scrape_facebook_ads, scrape_google_ads, scrape_linkedin_ads
from agent.tools.alt_tag_helper import extract_images_from_url
from agent.tools.google_search import find_competitor_sites
from agent.tools.memory_store import save_to_memory, search_memory

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

def get_context_from_text_or_url(text: str, url: str, customer_id: Optional[str] = None) -> str:
    """
    Liefert den sinnvollsten Kontext für den Prompt zurück – entweder Text, HTML oder Kundenspeicher.
    """
    text = text.strip() if text else ""
    url = url.strip() if url else ""

    if text:
        return text

    if url:
        try:
            return load_html(url)
        except Exception as e:
            return f"[Fehler beim Laden der URL {url}: {e}]"

    if customer_id:
        memory = load_customer_memory(customer_id)
        if memory:
            return memory

    raise ValueError("Kein verwertbarer Inhalt vorhanden (Text, URL oder Kunden-Memory).")

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

def fetch_trends_insights(keywords: List[str], timeframe: str = "now 7-d") -> str:
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
                    insights.append(f"- Suchinteresse für '{kw}': Änderung um {change} Punkte")
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
                value = data.get("value", "n/a")
                stats.append(f"- {code}: {value}")
        except Exception:
            continue
    return "\n".join(stats)

def run_agent(task: str, reasoning_mode: str = "fast", conversation_id: Optional[str] = None,
              clarifications: Optional[Dict[str, str]] = None, **kwargs: Any) -> Dict[str, Any]:
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    rss_snippets = trends_insights = destatis_stats = ""
    facebook_ads = google_ads = linkedin_ads = ""

    if reasoning_mode == "deep":
        rss_snippets = fetch_rss_snippets(kwargs.get("rss_feeds", []))
        trends_insights = fetch_trends_insights(kwargs.get("trend_keywords", []))
        destatis_stats = fetch_destatis_stats(kwargs.get("destatis_queries", []))

    # Fallback: Automatische Quellen basierend auf erkannter Themenliste
    rss_snippets = kwargs.get("rss_snippets", [])
    trends_insights = kwargs.get("trends_insights", [])
    destatis_stats = kwargs.get("destatis_stats", [])
    google_ads = kwargs.get("google_ads", [])
    facebook_ads = kwargs.get("facebook_ads", [])
    linkedin_ads = kwargs.get("linkedin_ads", [])

    keywords = kwargs.get("topic_keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(",") if k.strip()]
    elif isinstance(keywords, list):
        keywords = [k.strip() for k in keywords if isinstance(k, str) and k.strip()]
    else:
        keywords = []

    if keywords:
        if not rss_snippets:
            rss_snippets = fetch_rss_snippets([f"https://news.google.com/rss/search?q={kw}" for kw in keywords])
        if not trends_insights:
            trends_insights = fetch_trends_insights(keywords)
        if not destatis_stats:
            destatis_stats = fetch_destatis_stats(keywords)


    if task == "content_analysis":
        ctx = get_context_from_text_or_url(kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id"))
        tmpl = content_analysis_prompt_fast if reasoning_mode == "fast" else content_analysis_prompt_deep
        prompt = tmpl.format(
            context=ctx,
            rss_snippets=rss_snippets,
            trends_insights=trends_insights,
            destatis_stats=destatis_stats
        )

    elif task == "content_writing":
        zg = kwargs.get("zielgruppe") or ""
        ton = kwargs.get("tonalitaet") or ""
        th  = kwargs.get("thema") or ""

        # Diese Prüfung nur beim ersten Call, nicht bei Rückfragen
        if kwargs.get("is_follow_up") != True and not all([zg, ton, th]):
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

    elif task == "competitive_analysis":
        ctx_k = load_html(kwargs.get("eigene_url", ""))
        mitbewerber_urls = kwargs.get("wettbewerber_urls", [])
        mitbewerber_kontexte = []
        for url in mitbewerber_urls:
            try:
                ctx_m = load_html(url.strip())
                mitbewerber_kontexte.append(ctx_m)
            except Exception as e:
                mitbewerber_kontexte.append(f"[Fehler beim Laden von {url}: {e}]")
        if not mitbewerber_urls:
            suche = f"{kwargs.get('branche', '')} {kwargs.get('zielgruppe', '')} Anbieter"
            competitor_sites = find_competitor_sites(suche, max_results=2)

            for site in competitor_sites:
                try:
                    ctx_m = load_html(site)
                    mitbewerber_kontexte.append(ctx_m)
                except Exception as e:
                    mitbewerber_kontexte.append(f"[Fehler beim Laden von {site}: {e}]")

        if reasoning_mode == "deep":
            themenbegriffe = kwargs.get("ads_keywords", [])
            company = kwargs.get("customer_name", "")
            if kwargs.get("facebook_company"):
                facebook_ads = scrape_facebook_ads(company, themenbegriffe)
            if kwargs.get("google_company"):
                google_ads = scrape_google_ads(company, themenbegriffe)
            if kwargs.get("linkedin_company"):
                linkedin_ads = scrape_linkedin_ads(company, themenbegriffe)

        tmpl = competitive_analysis_prompt_fast if reasoning_mode == "fast" else competitive_analysis_prompt_deep
        prompt = tmpl.format(
            contexts_combined_kunde=ctx_k,
            contexts_combined_mitbewerber="\n\n---\n\n".join(mitbewerber_kontexte),
            rss_snippets=rss_snippets,
            trends_insights=trends_insights,
            google_ads=google_ads,
            facebook_ads=facebook_ads,
            linkedin_ads=linkedin_ads
        )

    elif task == "seo_audit":
        url = kwargs.get("url", "")
        zielgruppe = kwargs.get("zielgruppe", "")
        thema = kwargs.get("thema", "")
        keywords = kwargs.get("topic_keywords", [])
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)

        html = load_html(url)
        seo = extract_seo_signals(html)

        tmpl = seo_audit_prompt_fast if reasoning_mode == "fast" else seo_audit_prompt_deep

        prompt = tmpl.format(
            title=seo.get("title", ""),
            description=seo.get("description", ""),
            headlines=seo.get("headlines", []),
            text=seo.get("text", ""),
            zielgruppe=zielgruppe,
            thema=thema,
            keywords=keywords
        )

        result = call_llm(prompt)
        return {"response": result, "prompt_used": prompt}


    elif task in ["seo_optimize", "seo_optimization"]:
        txt = kwargs.get("text", "")
        url = kwargs.get("url", "")
        audit_pdf = kwargs.get("pdf_path")
        full = get_context_from_text_or_url(txt, url, kwargs.get("customer_id"))
        if url:
            full += "\n\nWebsite-Text:\n" + load_html(url)
            full += "\n\nSEO-Signale:\n" + json.dumps(extract_seo_signals(url), indent=2)
        if audit_pdf and os.path.exists(audit_pdf):
            full += "\n\nSEO Audit Report:\n" + load_pdf(audit_pdf)
        tmpl = (
            seo_optimization_prompt_fast
            if reasoning_mode == "fast"
            else seo_optimization_prompt_deep
        )
        prompt = tmpl.format(context=full)
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}


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
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "seo_lighthouse":
        url = kwargs.get("url", "")
        zielgruppe = kwargs.get("zielgruppe", "")
        thema = kwargs.get("thema", "")

        lighthouse_data = "(Keine Lighthouse-Daten verfügbar)"
        try:
            raw_lh = run_lighthouse(url)
            if isinstance(raw_lh, dict):
                lighthouse_data = json.dumps(raw_lh.get("categories", {}).get("seo", {}), indent=2)
        except Exception as e:
            lighthouse_data = f"[Fehler: {e}]"

        # 🧠 Kontexttext für den Prompt ergänzen (aus Text, URL oder Customer Memory)
        ctx = get_context_from_text_or_url(kwargs.get("text", ""), url, kwargs.get("customer_id"))

        tmpl = seo_lighthouse_prompt_fast if reasoning_mode == "fast" else seo_lighthouse_prompt_deep
        prompt = tmpl.format(
            context=ctx,
            url=url,
            zielgruppe=zielgruppe,
            thema=thema,
            lighthouse_data=lighthouse_data
        )
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}


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
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}


    elif task == "monthly_report":
        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id")
        )
        pdfp = kwargs.get("pdf_path")
        if pdfp and os.path.exists(pdfp):
            ctx += "\n\nPDF Anhang:\n" + load_pdf(pdfp)
        tmpl = (monthly_report_prompt_fast
                if reasoning_mode == "fast"
                else monthly_report_prompt_deep)
        prompt = tmpl.format(context=ctx)
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}


    elif task == "tactical_actions":
        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""), kwargs.get("url", ""), kwargs.get("customer_id")
        )
        pdfp = kwargs.get("pdf_path")
        if pdfp and os.path.exists(pdfp):
            ctx += "\n\n[Ergänzende Analyse aus PDF]:\n" + load_pdf(pdfp)
        tmpl = (tactical_actions_prompt_fast
                if reasoning_mode == "fast"
                else tactical_actions_prompt_deep)
        prompt = tmpl.format(context=ctx)
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}


    elif task == "alt_tag_writer":
        url = kwargs.get("url", "")
        branche = kwargs.get("branche", "Allgemein")
        zielgruppe = kwargs.get("zielgruppe", "Kunden")
        text = kwargs.get("text", "")

        image_data = extract_images_from_url(url)
        if isinstance(image_data, list):
            img_context_lines = []
            for idx, img in enumerate(image_data[:13], 1):
                img_context_lines.append(f"Bild {idx}: {img['src']}")
                if img["context"]:
                    img_context_lines.append(f"Kontext: {img['context']}")
            image_context = "\n".join(img_context_lines)
        else:
            image_context = f"[Fehler beim Laden der Bilder: {image_data.get('error')}]"

        from agent.prompts import alt_tag_writer_prompt_fast, alt_tag_writer_prompt_deep

        tmpl = alt_tag_writer_prompt_fast if reasoning_mode == "fast" else alt_tag_writer_prompt_deep

        prompt = tmpl.format(
            url=url,
            branche=branche,
            zielgruppe=zielgruppe,
            text=text,
            image_context=image_context
        )

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "extract_topics":
        # Für automatische Themenvorschläge (RSS/Trends/DESTATIS)
        txt = kwargs.get("text", "")
        if not txt:
            raise ValueError("Text zur Themenextraktion fehlt.")

        prompt = f"""
    Extrahiere maximal 5 relevante, aktuelle Themen oder Begriffe aus folgendem Inputtext. 
    Diese sollen sich für weitere Recherche in Google Trends, RSS-News oder DESTATIS eignen.

    Text:
    {txt}
    """

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "memory_write":
        save_to_memory([kwargs.get("text", "")])
        return {"response": "✅ Wissen gespeichert."}

    elif task == "memory_search":
        hits = search_memory(kwargs.get("query", ""))
        return {"response": "\n\n".join([doc.page_content for doc in hits])}

    else:
        raise ValueError(f"Unbekannter Task: {task}")

    if reasoning_mode == "deep" and clarifications:
        prompt = merge_clarifications(prompt, clarifications)

    try:
        resp = llm.invoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)

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

        log_event({
            "type": "task_complete",
            "customer_id": kwargs.get("customer_id"),
            "task": task,
            "mode": reasoning_mode
        })

        return {
            "response": content,
            "questions": extract_questions_from_response(content),
            "conversation_id": conversation_id
        }

    except Exception as e:
        log_event({
            "type": "error",
            "customer_id": kwargs.get("customer_id"),
            "task": task,
            "mode": reasoning_mode,
            "error": str(e)
        })
        raise

    content = resp.content if hasattr(resp, "content") else str(resp)

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

    log_event({
        "type": "task_complete",
        "customer_id": kwargs.get("customer_id"),
        "task": task,
        "mode": reasoning_mode
    })

    return {"response": content, "questions": extract_questions_from_response(content), "conversation_id": conversation_id}

