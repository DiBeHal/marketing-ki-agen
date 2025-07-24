from langchain_openai import ChatOpenAI
from agent.prompts import (
    content_briefing_prompt,
    content_write_prompt,
    competitive_analysis_prompt,
    seo_audit_prompt,
    seo_optimization_prompt,
    campaign_plan_prompt,
    seo_lighthouse_prompt,
    landingpage_strategy_contextual_prompt,
    monthly_report_prompt,
    tactical_actions_prompt
)
from agent.tools.lighthouse_runner import run_lighthouse
from agent.loader import load_html, extract_seo_signals, load_pdf
import json
import os

llm = ChatOpenAI(model="gpt-4o")

def search_google(brand_or_domain):
    return [
        f"https://www.linkedin.com/company/{brand_or_domain}",
        f"https://news.google.com/search?q={brand_or_domain}"
    ]

def get_context_from_text_or_url(text: str, url: str):
    context = ""
    if text and len(text.strip().split()) > 50:
        context += text.strip()
    if url:
        try:
            html_text = load_html(url)
            context += "\n" + html_text
        except Exception as e:
            context += f"\n[Fehler beim Laden von {url}: {e}]"
    if not context.strip():
        raise ValueError("Kein verwertbarer Inhalt vorhanden (Text oder URL).")
    return context

def run_agent(mode: str, **kwargs):
    if mode in ["briefing_overview", "briefing_analysis"]:
        context = get_context_from_text_or_url(kwargs.get("text", ""), kwargs.get("url", ""))
        prompt = content_briefing_prompt.format(context=context)
        return llm.invoke(prompt).content

    elif mode == "briefing_write":
        zielgruppe = kwargs.get("zielgruppe")
        tonalitaet = kwargs.get("tonalitaet")
        thema = kwargs.get("thema")
        if not all([zielgruppe, tonalitaet, thema]):
            raise ValueError("Zielgruppe, Tonalität und Thema sind Pflichtfelder.")
        prompt = content_write_prompt.format(
            zielgruppe=zielgruppe,
            tonalitaet=tonalitaet,
            thema=thema
        )
        return llm.invoke(prompt).content

    elif mode == "vergleich":
        if kwargs.get("eigene_url") and kwargs.get("wettbewerber_urls"):
            context_kunde = load_html(kwargs["eigene_url"])
            ergebnisse = []
            for url in kwargs["wettbewerber_urls"]:
                try:
                    context_mitbewerber = load_html(url.strip())
                    for link in search_google(url.strip()):
                        context_mitbewerber += "\n" + load_html(link)
                    prompt = competitive_analysis_prompt.format(
                        context_kunde=context_kunde,
                        context_mitbewerber=context_mitbewerber
                    )
                    result = llm.invoke(prompt).content
                    ergebnisse.append(f"🔗 {url}\n{result}")
                except Exception as e:
                    ergebnisse.append(f"❌ Fehler bei {url}: {str(e)}")
            return "\n\n---\n\n".join(ergebnisse)
        else:
            context_kunde = kwargs.get("text_kunde")
            context_mitbewerber = kwargs.get("text_mitbewerber")
            if not context_kunde or not context_mitbewerber:
                raise ValueError("Beide Texte (Kunde & Mitbewerber) werden benötigt")
            prompt = competitive_analysis_prompt.format(
                context_kunde=context_kunde,
                context_mitbewerber=context_mitbewerber
            )
            return llm.invoke(prompt).content

    elif mode == "seo_audit":
        url = kwargs.get("url")
        text = kwargs.get("text", "")
        context = get_context_from_text_or_url(text, url)

        signals = extract_seo_signals(url)
        try:
            lighthouse = run_lighthouse(url) if url else {}
            lighthouse_score = lighthouse.get("categories", {}).get("seo", {})
        except EnvironmentError as e:
            lighthouse_score = {"warnung": str(e)}

        combined_context = f"TEXT-INHALT:\n{context}\n\nTECHNIK:\n{json.dumps(signals, indent=2)}\n\nLIGHTHOUSE:\n{json.dumps(lighthouse_score, indent=2)}"
        prompt = seo_audit_prompt.format(context=combined_context)
        return llm.invoke(prompt).content

    elif mode == "seo_optimize":
        url = kwargs.get("url")
        context = kwargs.get("text", "")
        audit_pdf_path = kwargs.get("audit_pdf_path")
        audit_text = load_pdf(audit_pdf_path) if audit_pdf_path else ""

        full_context = context
        if url:
            html_text = load_html(url)
            seo_signals = extract_seo_signals(url)
            full_context += f"\n\nWebsite-Text:\n{html_text}"
            full_context += f"\n\nSEO-Signale:\n{json.dumps(seo_signals, indent=2)}"
        if audit_text:
            full_context += f"\n\nSEO Audit Report:\n{audit_text}"

        checklist = """
Berücksichtige für deine Optimierung folgende Bereiche:
1. On-Page-SEO (H-Struktur, Meta-Daten, interne Verlinkung)
2. Technisches SEO (Performance, Strukturierte Daten, Mobile UX)
3. Content-Marketing (Themenideen, Erweiterung)
4. Off-Page-SEO (Backlinks, Erwähnungen)
5. Lokales SEO (Google Business, Standortoptimierung)
6. Markups & strukturierte Daten (Schema.org, FAQ, Article, LocalBusiness etc.)
7. LLM-Optimierung (AIO, AEO, GEO für besseres AI-Auffinden & Verstehen)
"""

        prompt = f"""
{checklist}

Analysiere den gegebenen Kontext und gib eine priorisierte SEO-Roadmap aus:

- ✅ Kurzfristige Maßnahmen (1–7 Tage):
- 🔄 Mittelfristige Maßnahmen (2–4 Wochen):
- 🚀 Langfristige Empfehlungen (4+ Wochen):

Generiere zusätzlich einen konkreten optimierten Beispieltext für die analysierte Seite.
Erkläre abschließend, warum du diese Änderungen vorgenommen hast.

Kontext:
{full_context}
"""
        return llm.invoke(prompt).content

    elif mode == "campaign_plan":
        context = get_context_from_text_or_url(kwargs.get("text", ""), kwargs.get("url", ""))
        campaign_prompt = campaign_plan_prompt.format(context=context)
        return llm.invoke(campaign_prompt).content

    elif mode == "seo_lighthouse":
        url = kwargs.get("url")
        if not url:
            raise ValueError("URL für Lighthouse-Analyse fehlt.")
        try:
            report = run_lighthouse(url)
            seo_data = json.dumps(report["categories"]["seo"], indent=2)
        except EnvironmentError as e:
            seo_data = json.dumps({"warnung": str(e)}, indent=2)
        prompt = seo_lighthouse_prompt.format(context=seo_data)
        return llm.invoke(prompt).content

    elif mode == "landingpage_strategy":
        url = kwargs.get("url", "")
        text = kwargs.get("text", "")
        pdf_path = kwargs.get("pdf_path", "")

        context_website = load_html(url) if url else text
        context_anhang = load_pdf(pdf_path) if pdf_path else ""

        prompt = landingpage_strategy_contextual_prompt.format(
            context_website=context_website,
            context_anhang=context_anhang
        )
        return llm.invoke(prompt).content

    elif mode == "monthly_report":
        context = get_context_from_text_or_url(kwargs.get("text", ""), kwargs.get("url", ""))
        audit_pdf_path = kwargs.get("audit_pdf_path")
        if audit_pdf_path and os.path.exists(audit_pdf_path):
            context += f"\n\nPDF Anhang:\n{load_pdf(audit_pdf_path)}"
        prompt = monthly_report_prompt.format(context=context)
        return llm.invoke(prompt).content

    elif mode == "tactical_actions":
        context = get_context_from_text_or_url(kwargs.get("text", ""), kwargs.get("url", ""))
        audit_pdf_path = kwargs.get("audit_pdf_path")
        if audit_pdf_path and os.path.exists(audit_pdf_path):
            context += f"\n\n[Ergänzende Analyse aus PDF]:\n{load_pdf(audit_pdf_path)}"
        prompt = tactical_actions_prompt.format(context=context)
        return llm.invoke(prompt).content

    else:
        raise ValueError(f"Unbekannter Modus: {mode}")
