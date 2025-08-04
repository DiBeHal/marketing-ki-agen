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

from agent.tools.context_utils import get_context_from_text_or_url

def has_any(*args):
    return any(arg and str(arg).strip() for arg in args)

def check_task_requirements(task: str, kwargs: dict):
    requirements = TASK_REQUIREMENTS.get(task, {})

    for key, rule in requirements.items():
        if rule == "required" and not kwargs.get(key):
            raise ValueError(f"Task '{task}' benötigt zwingend: {key}")
        if rule == "any_of":
            if not has_any(*[kwargs.get(k) for k in key.split("|")]):
                raise ValueError(f"Task '{task}' benötigt mindestens einen dieser Werte: {key}")

TASK_REQUIREMENTS = {
    "seo_audit": {
        "url": "required"
    },
    "seo_optimization": {
        "text|url|customer_id": "any_of"
    },
    "seo_lighthouse": {
        "url": "required"
    },
    "content_analysis": {
        "text|url|customer_id": "any_of"
    },
    "content_writing": {
        "zielgruppe": "required",
        "tonalitaet": "required",
        "thema": "required"
    },
    "campaign_plan": {
        "text|url|customer_id": "any_of",
        "zielgruppe": "required",
        "thema": "required"
    },
    "landingpage_strategy": {
        "url": "required"
    },
    "tactical_actions": {
        "text|url|customer_id": "any_of"
    },
    "alt_tag_writer": {
        "url": "required"
    },
    "extract_topics": {
        "text": "required"
    }
}

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
    extract_topics_prompt_deep
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
from agent.tools.scraper import scrape_html, extract_image_sources
from agent.tools.parser import extract_text_blocks


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

from agent.tools.scraper import scrape_html
from agent.tools.parser import extract_text_blocks

def load_html(path_or_url):
    if not path_or_url.startswith("http"):
        path_or_url = "https://" + path_or_url

    try:
        html = scrape_html(path_or_url)
        text_blocks = extract_text_blocks(html)
        return "\n".join(text_blocks)
    except Exception as e:
        raise ValueError(f"Fehler beim Abrufen oder Parsen der URL {path_or_url}: {e}")

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

def run_agent(task: str, conversation_id: Optional[str] = None,
              clarifications: Optional[Dict[str, str]] = None, **kwargs: Any) -> Dict[str, Any]:
    if conversation_id is None:
        conversation_id = str(uuid.uuid4())

    rss_snippets = trends_insights = destatis_stats = ""
    facebook_ads = google_ads = linkedin_ads = ""

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
        check_task_requirements(task, kwargs)
        if not any([
            kwargs.get("text", "").strip(),
            kwargs.get("url", "").strip(),
            kwargs.get("customer_id"),
            kwargs.get("pdf_path")
        ]):
            raise ValueError("❗ Kein Kontext übergeben – bitte Text, URL, Kunden-ID oder PDF angeben.")

        zielgruppe = kwargs.get("zielgruppe", "Zielgruppe nicht angegeben")
        thema = kwargs.get("thema", "Kein Thema angegeben")

        ctx = ""
        if kwargs.get("text", "").strip():
            ctx = kwargs["text"]
        elif kwargs.get("url", ""):
            try:
                html = scrape_html(kwargs["url"])
                ctx = "\n".join(extract_text_blocks(html))
            except Exception as e:
                ctx = f"[Fehler beim Laden und Parsen von URL: {e}]"

        if not ctx and kwargs.get("customer_id"):
            ctx = load_customer_memory(kwargs["customer_id"])

        if not ctx and kwargs.get("pdf_path") and os.path.exists(kwargs["pdf_path"]):
            ctx = load_pdf(kwargs["pdf_path"])


        tmpl = content_analysis_prompt_deep
        prompt = tmpl.format(
            context=ctx,
            zielgruppe=zielgruppe,
            thema=thema,
            rss_snippets=rss_snippets,
            trends_insights=trends_insights,
            destatis_stats=destatis_stats
        )
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "content_writing":
        check_task_requirements(task, kwargs)
        zielgruppe = kwargs.get("zielgruppe", "Zielgruppe nicht angegeben").strip()
        tonalitaet = kwargs.get("tonalitaet", "Neutral").strip()
        thema = kwargs.get("thema", "Kein Thema angegeben").strip()
        rss_snippets = kwargs.get("rss_snippets", "[Keine RSS-Daten]")
        trends_insights = kwargs.get("trends_insights", "[Keine Trenddaten]")
        destatis_stats = kwargs.get("destatis_stats", "[Keine Marktdaten]")
        format_laenge = kwargs.get("format_laenge", "")


        ctx = get_context_from_text_or_url(
            kwargs.get("text", ""),
            kwargs.get("url", ""),
            kwargs.get("customer_id"),
            kwargs.get("pdf_path")
        )

        tmpl = content_write_prompt_deep

        prompt = tmpl.format(
            context=ctx,
            zielgruppe=zielgruppe,
            tonalitaet=tonalitaet,
            thema=thema,
            format_laenge=format_laenge,
            rss_snippets=rss_snippets,
            trends_insights=trends_insights,
            destatis_stats=destatis_stats
        )
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "competitive_analysis":
        check_task_requirements(task, kwargs)

        try:
            ctx_k = get_context_from_text_or_url(
                kwargs.get("text", ""),
                kwargs.get("eigene_url", "") or kwargs.get("url", ""),
                kwargs.get("customer_id"),
                kwargs.get("pdf_path")
            )
        except Exception as e:
            ctx_k = f"[Fehler beim Laden des Kundenkontexts: {e}]"

        # Mitbewerber-Kontexte (aus URLs oder Namen)
        mitbewerber_urls = kwargs.get("wettbewerber_urls", [])
        mitbewerber_namen = kwargs.get("wettbewerber_namen", [])
        mitbewerber_kontexte = []

        for url in mitbewerber_urls:
            try:
                ctx_m = load_html(url.strip())
                mitbewerber_kontexte.append(f"{url}:\n{ctx_m}")
            except Exception as e:
                mitbewerber_kontexte.append(f"[Fehler beim Laden von {url}: {e}]")

        for name in mitbewerber_namen:
            try:
                sites = find_competitor_sites(name, max_results=1)
                if sites:
                    html = load_html(sites[0])
                    mitbewerber_kontexte.append(f"{name} ({sites[0]}):\n{html}")
                else:
                    mitbewerber_kontexte.append(f"[Keine Webseite für {name} gefunden]")
            except Exception as e:
                mitbewerber_kontexte.append(f"[Fehler bei Recherche {name}: {e}]")

        if not mitbewerber_urls and not mitbewerber_namen:
            suche = f"{kwargs.get('branche', '')} {kwargs.get('zielgruppe', '')} Anbieter"
            competitor_sites = find_competitor_sites(suche, max_results=2)
            for site in competitor_sites:
                try:
                    ctx_m = load_html(site)
                    mitbewerber_kontexte.append(f"{site}:\n{ctx_m}")
                except Exception as e:
                    mitbewerber_kontexte.append(f"[Fehler beim Laden von {site}: {e}]")

        # Ads-Analyse
        google_ads = facebook_ads = linkedin_ads = "[Keine Daten]"
        themenbegriffe = kwargs.get("ads_keywords", [])
        company = kwargs.get("customer_name", "")
        if kwargs.get("facebook_company"):
            facebook_ads = scrape_facebook_ads(company, themenbegriffe)
        if kwargs.get("google_company"):
            google_ads = scrape_google_ads(company, themenbegriffe)
        if kwargs.get("linkedin_company"):
            linkedin_ads = scrape_linkedin_ads(company, themenbegriffe)

        # Prompt
        prompt = competitive_analysis_prompt_deep.format(
            kunde_name=kwargs.get("customer_name", "Unsere Firma"),
            branche=kwargs.get("branche", "Allgemein"),
            zielgruppe=kwargs.get("zielgruppe", "Kunden"),
            contexts_combined_kunde=ctx_k,
            contexts_combined_mitbewerber="\n\n---\n\n".join(mitbewerber_kontexte),
            google_ads=google_ads,
            facebook_ads=facebook_ads,
            linkedin_ads=linkedin_ads
        )

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "seo_audit":
        check_task_requirements(task, kwargs)

        try:
            ctx = get_context_from_text_or_url(
                kwargs.get("text", ""),
                kwargs.get("url", ""),
                kwargs.get("customer_id"),
                kwargs.get("pdf_path")
            )
        except Exception as e:
            ctx = f"[Fehler beim Laden des Kontexts: {e}]"

        url = kwargs.get("url", "")
        zielgruppe = kwargs.get("zielgruppe", "Zielgruppe nicht angegeben")
        thema = kwargs.get("thema", "Kein Thema angegeben")
        keywords = kwargs.get("topic_keywords", [])
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)

        try:
            seo_signals = extract_seo_signals(url)
            title = seo_signals.get("title", "")
            meta_description = seo_signals.get("meta_description", "")
            headings = "\n".join(seo_signals.get("headings", []))
            num_links = seo_signals.get("num_links", 0)
            cta_links = seo_signals.get("cta_links", 0)
        except Exception as e:
            title = meta_description = headings = ""
            num_links = cta_links = 0
            ctx += f"\n[Fehler beim SEO-Signale-Laden: {e}]"

        tmpl = seo_audit_prompt_deep
        prompt = tmpl.format(
            contexts_combined=ctx,
            zielgruppe=zielgruppe,
            thema=thema,
            keywords=keywords,
            title=title,
            meta_description=meta_description,
            headings=headings,
            num_links=num_links,
            cta_links=cta_links,
            rss_snippets=kwargs.get("rss_snippets", "[Keine RSS-Daten]"),
            trends_insights=kwargs.get("trends_insights", "[Keine Trenddaten]"),
            destatis_stats=kwargs.get("destatis_stats", "[Keine Marktdaten]")
        )

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task in ["seo_optimize", "seo_optimization"]:
        check_task_requirements("seo_optimization", kwargs)
        focus_url = kwargs.get("url", "")

        try:
            ctx = get_context_from_text_or_url(
                kwargs.get("text", ""),
                kwargs.get("url", ""),
                kwargs.get("customer_id"),
                kwargs.get("pdf_path")
            )
        except Exception as e:
            ctx = f"[Fehler beim Laden des Kontexts: {e}]"

        tmpl = seo_optimization_prompt_deep
        prompt = tmpl.format(
            contexts_combined=ctx,
            focus_url=focus_url,
            seo_audit_summary=kwargs.get("seo_audit_summary", "[Keine SEO-Audit-Zusammenfassung]"),
            lighthouse_json=kwargs.get("lighthouse_json", "[Keine Lighthouse-Daten]"),
            zielgruppe=kwargs.get("zielgruppe", "Zielgruppe nicht angegeben"),
            ziel=kwargs.get("ziel", "Ziel nicht angegeben"),
            thema=kwargs.get("thema", "Kein Thema angegeben"),
            rss_snippets=kwargs.get("rss_snippets", "[Keine RSS-Daten]"),
            trends_insights=kwargs.get("trends_insights", "[Keine Trenddaten]"),
            destatis_stats=kwargs.get("destatis_stats", "[Keine Marktdaten]")
        )


        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}


    elif task == "campaign_plan":
        check_task_requirements(task, kwargs)
        produkt = kwargs.get("produkt", "Nicht angegeben")
        zeitraum = kwargs.get("zeitraum", "Nicht definiert")

        if not any([
            kwargs.get("text", "").strip(),
            kwargs.get("url", "").strip(),
            kwargs.get("customer_id"),
            kwargs.get("pdf_path")
        ]):
            raise ValueError("❗ Kein Kontext vorhanden – bitte Text, URL, Kunden-ID oder PDF angeben.")

        ctx = ""
        if kwargs.get("text", "").strip():
            ctx = kwargs["text"]
        elif kwargs.get("url", ""):
            try:
                html = scrape_html(kwargs["url"])
                ctx = "\n".join(extract_text_blocks(html))
            except Exception as e:
                ctx = f"[Fehler beim Laden und Parsen von URL: {e}]"

        if not ctx and kwargs.get("customer_id"):
            ctx = load_customer_memory(kwargs["customer_id"])

        if not ctx and kwargs.get("pdf_path") and os.path.exists(kwargs["pdf_path"]):
            ctx = load_pdf(kwargs["pdf_path"])


        zg = kwargs.get("zielgruppe", "")
        th = kwargs.get("thema", "")

        tmpl = campaign_plan_prompt_deep
        prompt = tmpl.format(
            context=ctx,
            zielgruppe=kwargs.get("zielgruppe", ""),
            thema=kwargs.get("thema", ""),
            ziel=kwargs.get("ziel", "Nicht angegeben"),
            produkt=produkt,
            zeitraum=zeitraum,
            rss_snippets=kwargs.get("rss_snippets", "[Keine RSS-Daten]"),
            trends_insights=kwargs.get("trends_insights", "[Keine Trenddaten]"),
            destatis_stats=kwargs.get("destatis_stats", "[Keine Marktdaten]")
        )

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "seo_lighthouse":
        check_task_requirements(task, kwargs)

        zielgruppe = kwargs.get("zielgruppe", "Zielgruppe nicht angegeben")
        thema = kwargs.get("thema", "Kein Thema angegeben")
        branche = kwargs.get("branche", "Allgemein")
        context_text = kwargs.get("text", "").strip()
        urls = kwargs.get("urls", [])
        customer_id = kwargs.get("customer_id")
        pdf_path = kwargs.get("pdf_path")

        if not urls:
            raise ValueError("❗ Bitte mindestens eine URL angeben.")

        analyses = []

        for url in urls:
            # Kontext pro Seite
            try:
                ctx = get_context_from_text_or_url(context_text, url, customer_id, pdf_path)
            except Exception as e:
                ctx = f"[Fehler beim Laden des Kontexts: {e}]"


            # Lighthouse-Daten sammeln
            lighthouse_data = "(Keine Lighthouse-Daten verfügbar)"
            try:
                raw_lh = run_lighthouse(url)
                if isinstance(raw_lh, dict):
                    lighthouse_data = json.dumps(raw_lh.get("categories", {}).get("seo", {}), indent=2)
            except Exception as e:
                lighthouse_data = f"[Fehler bei Lighthouse-Analyse: {e}]"

            analyses.append({
                "url": url,
                "context_website": ctx,
                "lighthouse": lighthouse_data
            })

        # Prompt-Vorbereitung
        combined_blocks = []
        for a in analyses:
            combined_blocks.append(f"""=== {a['url']} ===

    Website-Kontext:
    {a['context_website']}

    Lighthouse-Report:
    {a['lighthouse']}""")

        combined_input = "\n\n".join(combined_blocks)
        # Prompt
        tmpl = seo_lighthouse_prompt_deep
        prompt = tmpl.format(
            context=context_text,
            context_website=combined_input,
            branche=branche,
            zielgruppe=zielgruppe,
            thema=thema,
            url="Mehrere URLs",
            lighthouse_reports_combined=lighthouse_data
        )

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}


    elif task == "landingpage_strategy":
        check_task_requirements(task, kwargs)

        if not kwargs.get("url", "").strip():
            raise ValueError("❗ Keine URL übergeben für Landingpage-Analyse.")

        try:
            html = scrape_html(kwargs["url"])
            ctx_web = "\n".join(extract_text_blocks(html))
        except Exception as e:
            ctx_web = f"[Fehler beim Laden und Parsen von URL: {e}]"

        ctx_att = ""
        pdfp = kwargs.get("pdf_path", "")
        if pdfp and os.path.exists(pdfp):
            ctx_att = load_pdf(pdfp)

        tmpl = landingpage_strategy_contextual_prompt_deep
        prompt = tmpl.format(
            context=context_text,
            context_website=combined_input,
            zielgruppe=kwargs.get("zielgruppe", "Zielgruppe nicht definiert").strip(),
            ziel=kwargs.get("ziel", "").strip(),
            thema=kwargs.get("angebot", "").strip(),
            rss_snippets=kwargs.get("rss_snippets", "[Keine RSS-Daten]"),
            trends_insights=kwargs.get("trends_insights", "[Keine Trenddaten]"),
            destatis_stats=kwargs.get("destatis_stats", "[Keine Destatis-Daten]"),
            google_ads=kwargs.get("google_ads", "[Keine Google Ads]"),
            facebook_ads=kwargs.get("facebook_ads", "[Keine Facebook Ads]"),
            linkedin_ads=kwargs.get("linkedin_ads", "[Keine LinkedIn Ads]")
        )

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "tactical_actions":
        check_task_requirements(task, kwargs)

        # Kontext extrahieren
        try:
            ctx = get_context_from_text_or_url(
                kwargs.get("text", ""),
                kwargs.get("url", ""),
                kwargs.get("customer_id"),
                kwargs.get("pdf_path")
            )
        except Exception as e:
            ctx = f"[Fehler beim Laden des Kontexts: {e}]"

        # Versuch automatische Themenextraktion, falls nicht manuell gesetzt
        topic_keywords = []
        try:
            theme_text = " ".join([
                kwargs.get("ziel", ""),
                kwargs.get("zeitfenster", ""),
                ctx
            ]).strip()

            if theme_text:
                extract_result = run_agent(
                    task="extract_topics",
                    text=theme_text
                )
                topic_keywords = extract_result["response"].strip().split("\n")
                topic_keywords = [t.strip("-• ").strip() for t in topic_keywords if len(t.strip()) > 3]
        except Exception as e:
            topic_keywords = []
            log_event({"type": "warning", "message": f"Topic-Extraktion fehlgeschlagen: {e}"})


        tmpl = tactical_actions_prompt_deep
        prompt = tmpl.format(
            context=ctx,
            ziel=kwargs.get("ziel", "Kein Ziel definiert"),
            zeitfenster=kwargs.get("zeitfenster", "Unbekannter Zeitraum"),
            rss_snippets=kwargs.get("rss_snippets", "[Keine RSS-Daten]"),
            trends_insights=kwargs.get("trends_insights", "[Keine Trenddaten]"),
            destatis_stats=kwargs.get("destatis_stats", "[Keine Marktdaten]"),
            keywords=", ".join(topic_keywords) if topic_keywords else "[Keine extrahierten Themen]",
            seo_summary=kwargs.get("seo_summary", "[Keine SEO-Zusammenfassung]")
        )

        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)
        return {"response": result, "prompt_used": prompt}

    elif task == "alt_tag_writer":
        check_task_requirements(task, kwargs)
        url = kwargs.get("url", "")
        branche = kwargs.get("branche", "Allgemein")
        zielgruppe = kwargs.get("zielgruppe", "Kunden")
        text = kwargs.get("text", "")
        include_svg = kwargs.get("include_svg", False)

        if not text and url:
            try:
                html = scrape_html(url)
                text = "\n".join(extract_text_blocks(html))
            except Exception as e:
                text = f"[Fehler beim Extrahieren von Text aus URL: {e}]"

        image_data = extract_images_from_url(url)

        if isinstance(image_data, list):
            filtered_images = [
                img for img in image_data
                if include_svg or not img["src"].lower().endswith(".svg")  # <- NEU
            ]
            limit = 40
            img_context_lines = []
            for idx, img in enumerate(filtered_images[:limit], 1):
                img_context_lines.append(f"Bild {idx}: {img['src']}")
                if img.get("context"):
                    img_context_lines.append(f"Kontext: {img['context']}")
            image_context = "\n".join(img_context_lines)
        else:
            image_context = f"[Fehler beim Laden der Bilder: {image_data.get('error')}]"

        from agent.prompts import alt_tag_writer_prompt_deep
        tmpl = alt_tag_writer_prompt_deep

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
        check_task_requirements(task, kwargs)

        text = kwargs.get("text", "").strip()
        if not text:
            # Versuch Kontext zu erzeugen aus URL, customer_id oder PDF
            try:
                text = get_context_from_text_or_url(
                    kwargs.get("text", ""),
                    kwargs.get("url", ""),
                    kwargs.get("customer_id"),
                    kwargs.get("pdf_path")
                ).strip()
            except Exception as e:
                raise ValueError(f"❗ Kein Text übergeben für Topic-Extraktion. (Fallback fehlgeschlagen: {e})")

        if not text:
            raise ValueError("❗ Kein Text übergeben für Topic-Extraktion.")

        from agent.prompts import extract_topics_prompt_deep  # Sicherstellen, dass oben importiert ist

        prompt = extract_topics_prompt_deep.format(text=text)
        resp = llm.invoke(prompt)
        result = resp.content if hasattr(resp, "content") else str(resp)

        return {"response": result.strip(), "prompt_used": prompt}

    elif task == "memory_write":
        check_task_requirements(task, kwargs)

        content = kwargs.get("text", "").strip()
        if not content:
            raise ValueError("Kein Inhalt zum Speichern übergeben.")

        customer_id = kwargs.get("customer_id", "")
        if not customer_id:
            raise ValueError("Kein Kunden-ID vorhanden.")

        append_customer_memory(customer_id, content)
        return {"response": f"🧠 Kontext gespeichert für Kunde {customer_id}."}


    elif task == "memory_search":
        query = kwargs.get("query", "").strip()
        if not query:
            raise ValueError("Kein Suchbegriff übergeben.")

        hits = search_memory(query)
        if not hits:
            return {"response": "❌ Keine passenden Inhalte im Memory gefunden."}

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
        "mode": "standard"
    })

    return {"response": content, "questions": extract_questions_from_response(content), "conversation_id": conversation_id}

