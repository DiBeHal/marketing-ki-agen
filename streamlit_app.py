# streamlit_app.py

import os
import hashlib
from dotenv import load_dotenv

import streamlit as st
import random
import string
import pandas as pd
from collections import Counter

from agent.customer_memory import (
    save_customer_data,
    list_customer_ids,
    load_customer_memory,
    save_customer_memory
)
from agent.loader import load_pdf
from agent.base_agent import run_agent
from agent.activity_log import log_event, get_events

# -----------------------------------------------------------------------------  
# Environment laden (lokal & Produktion)  
# -----------------------------------------------------------------------------
load_dotenv()

# -----------------------------------------------------------------------------  
# Einfache Authentifizierung  
# -----------------------------------------------------------------------------
def check_credentials(user: str, pwd: str) -> bool:
    expected_user = os.getenv("APP_USER")
    expected_hash = os.getenv("APP_PASS_HASH")
    return (
        user == expected_user
        and hashlib.sha256(pwd.encode()).hexdigest() == expected_hash
    )

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Login")
    user = st.text_input("Benutzername")
    pwd  = st.text_input("Passwort", type="password")
    if st.button("Anmelden"):
        if check_credentials(user, pwd):
            st.session_state.authenticated = True
        else:
            st.error("Ungültige Anmeldedaten")
    st.stop()

# -----------------------------------------------------------------------------  
# Nach erfolgreichem Login: Streamlit-Konfiguration  
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Kunden-Upload & KI-Agent", layout="wide")

# Persist Deep-Loop Session-State
for key in ('last_task', 'conv_id', 'questions', 'response'):
    if key not in st.session_state:
        st.session_state[key] = None if key in ('last_task', 'conv_id') else []

# -----------------------------------------------------------------------------  
# Sidebar: User- vs. Admin-Ansicht  
# -----------------------------------------------------------------------------
page = st.sidebar.selectbox("Ansicht wählen:", ["🎯 User-Tasks", "⚙️ Admin-Dashboard"])

# ===============================  
# Admin-Dashboard  
# ===============================
if page == "⚙️ Admin-Dashboard":
    st.title("⚙️ Admin-Dashboard")

    # Lade alle Events
    events = get_events()
    df = pd.DataFrame(events)
    if not df.empty:
        df.columns = df.columns.str.strip().str.lower()
        if "type" not in df.columns:
            st.warning("⚠️ Spalte 'type' nicht im Event-Log gefunden.")
            df["type"] = ""
    else:
        df = pd.DataFrame(columns=["type", "timestamp", "customer_id", "task", "rating", "comment", "mode", "input_tokens", "output_tokens"])

    # 1) Kunden-Übersicht
    st.subheader("🔹 Kunden-Übersicht")
    customers = list_customer_ids()
    overview = []
    for cid in customers:
        tasks = df[(df["type"] == "task_run") & (df["customer_id"] == cid)]
        last = tasks.sort_values('timestamp', ascending=False).head(3)
        last_str = "\n".join(f"{r['task']} @ {r['timestamp']}" for _, r in last.iterrows()) or "-"
        ratings = df[(df["type"] == "rating") & (df["customer_id"] == cid)]["rating"]
        avg = round(ratings.mean(), 2) if len(ratings) > 0 else "-"
        overview.append({"Kunden-ID": cid, "Letzte Tasks": last_str, "Ø Bewertung": avg})
    st.table(overview)

    # 2) Kosten & Token-Verbrauch
    st.subheader("💸 Kosten & Token-Verbrauch")
    usage = df[df["type"] == "usage"]
    if not usage.empty:
        usage_grp = (
            usage
            .groupby(['customer_id', 'mode'])
            .agg({'input_tokens': 'sum', 'output_tokens': 'sum'})
            .reset_index()
        )
        usage_grp['cost'] = (
            usage_grp['input_tokens'] * 0.00000465 +
            usage_grp['output_tokens'] * 0.00001395
        )
        st.dataframe(usage_grp)
        summary = usage_grp.groupby('customer_id')['cost'].sum().reset_index()
        summary = summary.set_index('customer_id')
        st.bar_chart(summary)

    else:
        st.info("Noch keine Usage-Daten.")

    # 3) Trend- & Zeitreihen-Analysen
    st.subheader("📈 Trend-Analysen")
    tasks_df = df[df["type"] == "task_run"]
    if not tasks_df.empty:
        daily_tasks = tasks_df.set_index('timestamp').resample('D').size().rename('tasks')
        st.line_chart(daily_tasks)
    else:
        st.info("Noch keine Task-Daten.")
    if not usage.empty:
        daily_usage = usage.set_index('timestamp').resample('D').sum()[['input_tokens','output_tokens']]
        st.area_chart(daily_usage)
    else:
        st.info("Noch keine Usage-Daten für Trend.")

    # 5) Aktivitätslog & CSV-Export
    st.subheader("📝 Aktivitätslog")
    if not df.empty:
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Export Log als CSV", data=csv, file_name="activity_log.csv", mime="text/csv")
    else:
        st.info("Noch keine Events geloggt.")

    # 6) Qualitäts- & Feedback-Loop
    st.subheader("🗣️ Feedback & Ratings")
    feedback = df[df["type"] == "rating"]
    if not feedback.empty:
        st.dataframe(feedback[['customer_id','rating','comment','timestamp']])
        words = Counter()
        for c in feedback['comment'].dropna():
            for w in c.lower().split():
                words[w] += 1
        st.write("Top 5 Feedback-Begriffe:", words.most_common(5))
    else:
        st.info("Noch kein Feedback vorhanden.")

    # 7) Interactive Drill-Downs
    st.subheader("🔍 Details pro Kunde")
    for cid in customers:
        with st.expander(f"Kunde {cid}"):
            st.write("Letzte Tasks", tasks_df[tasks_df["customer_id"] == cid][['task','timestamp']])
            st.write("Token Usage", usage[usage["customer_id"] == cid][['input_tokens','output_tokens','timestamp']])
            st.write("Feedback", feedback[feedback["customer_id"] == cid][['rating','comment','timestamp']])
            st.write("Rohes Log", df[df["customer_id"] == cid])

    st.stop()

# ===============================  
# User-Tasks  
# ===============================
st.title("👤 Kunden-Upload & KI-Agent")

# Initialisiere leeres params-Dictionary, damit es für spätere Blöcke existiert
params = {}

# Kundenprofil anlegen
customer_name = st.text_input("Name des neuen Kunden (z. B. Kosmetikstudio Müller)")
url_input     = st.text_input("Website-URL des Kunden")
pdf_file      = st.file_uploader("Optional: PDF-Datei mit Informationen zum Kunden", type=["pdf"])
notes         = st.text_area("Optional: Weitere Informationen zum Kunden")

if st.button("✅ Kundenprofil erstellen"):
    if not customer_name or not url_input:
        st.error("Bitte gib mindestens den Kundennamen und eine Website-URL an.")
    else:
        identifier = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        pdf_text = load_pdf(pdf_file) if pdf_file else ""
        save_customer_data(identifier, {
            "name": customer_name,
            "url": url_input,
            "pdf": pdf_text,
            "notes": notes
        })
        st.success(f"Kundenprofil erstellt. ID: {identifier}")

st.markdown("---")
st.header("🎯 Marketing-Tasks mit KI-Agent")

mode = "deep"


# ---------------------------------------
# 🧠 Gedächtnis-Verwaltung (FAISS)
# ---------------------------------------
with st.expander("🧠 Gedächtnis-Verwaltung (FAISS)", expanded=False):
    memory_col1, memory_col2 = st.columns(2)

    with memory_col1:
        if st.button("📥 Wissen speichern"):
            try:
                response = run_agent(
                    task="memory_write",
                    reasoning_mode=mode,
                    text=params.get("text", "")
                )
                st.success(response["response"])
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")

    with memory_col2:
        query = st.text_input("🔍 Gedächtnis durchsuchen", "")
        if query:
            try:
                response = run_agent(
                    task="memory_search",
                    reasoning_mode=mode,
                    query=query
                )
                st.info("Suchergebnisse:")
                st.write(response["response"])
            except Exception as e:
                st.error(f"Fehler bei der Suche: {e}")

st.markdown("🔍 Aktiver Modus: **Tiefenanalyse** (alle Aufgaben laufen in ausführlicher Analyse)")
task = st.selectbox("Wähle eine Aufgabe:", [
    "–",
    "Content Analyse",
    "Content Writing",
    "Wettbewerbsanalyse",
    "SEO Audit",
    "SEO Optimierung",
    "Technisches SEO (Lighthouse)",
    "Kampagnenplanung",
    "Landingpage Strategie",
    "Marketingmaßnahmen planen",
    "Alt-Tag Generator"
])

# Reset bei Task- oder Modus-Wechsel
if task != st.session_state.last_task:
    st.session_state.conv_id = None
    st.session_state.questions = []
    st.session_state.response = ""
    st.session_state.last_task = task
if "start_agent" not in st.session_state:
    st.session_state.start_agent = False


# Kundenkontext
customer_options = ["– Kein Kunde –"] + list_customer_ids()
selected_customer = st.selectbox("🧠 Ordne Analyse optional einem Kunden zu:", customer_options)
customer_id = selected_customer if selected_customer != "– Kein Kunde –" else None
customer_memory = load_customer_memory(customer_id) if customer_id else ""

# Gemeinsame Inputs
url = st.text_input("🌐 (Optional) Website-URL", placeholder="https://…")
context = st.text_area("📄 Optionaler Kontext/Text", height=200)
optional_pdf = st.file_uploader("📥 Optional: Kontext-PDF hochladen", type=["pdf"])
optional_pdf_path = None
if optional_pdf:
    optional_pdf_path = "optional_context.pdf"
    with open(optional_pdf_path, "wb") as f:
        f.write(optional_pdf.read())

# Task-spezifische Inputs
kunde = mitbewerber = eigene_url = wettbewerber_urls = None
briefing_typ = kanal = thema = zielgruppe = tonalitaet = ""

if task == "Content Analyse":
    task_id = "content_analysis"

    text_input = (customer_memory + "\n\n" + context).strip()

    if not text_input and not url.strip():
        st.error("❗ Bitte gib mindestens Kontexttext oder URL an.")
        st.stop()

    params = {
        "task": task_id,
        "text": text_input,
        "url": url.strip(),
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Content Writing":
    task_id = "content_writing"
    zielgruppe = st.text_input("👥 Zielgruppe")
    tonalitaet = st.text_input("🎙️ Tonalität")
    thema = st.text_input("📝 Thema")
    if not (zielgruppe and tonalitaet and thema):
        st.error("❗ Bitte Zielgruppe, Tonalität und Thema angeben.")
        st.stop()
    combined_context = (customer_memory + "\n\n" + context).strip()
    if not (combined_context or url.strip() or optional_pdf_path):
        st.error("❗ Bitte gib mindestens Kontexttext, URL oder PDF an.")
        st.stop()
    params = {
        "task": task_id,
        "zielgruppe": zielgruppe,
        "tonalitaet": tonalitaet,
        "thema": thema,
        "text": customer_memory + "\n\n" + context,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Wettbewerbsanalyse":
    task_id = "competitive_analysis"

    eigene_url = st.text_input("🌐 Eigene Website")
    wettbewerber_urls_input = st.text_area("🏢 Wettbewerber-URLs (eine pro Zeile)", height=150, placeholder="https://www.firma-a.de\nhttps://www.firma-b.de")
    wettbewerber_namen_input = st.text_area("🔠 Wettbewerber-Namen (eine pro Zeile)", height=150, placeholder="Firma A\nFirma B")

    wettbewerber_urls = [url.strip() for url in wettbewerber_urls_input.split("\n") if url.strip()]
    wettbewerber_namen = [name.strip() for name in wettbewerber_namen_input.split("\n") if name.strip()]

    if not eigene_url:
        st.error("❗ Bitte eigene Website angeben.")
        st.stop()

    st.subheader("📊 Optional: Werbebibliotheken einbeziehen")
    facebook = st.checkbox("📘 Facebook Ads Library einbeziehen?")
    google = st.checkbox("🔍 Google Ads Transparency Center einbeziehen?")
    linkedin = st.checkbox("💼 LinkedIn Ads Library einbeziehen?")

    ads_themen_input = st.text_input("🔎 Themen/Produkte für Werbeanalyse (kommagetrennt)")
    ads_themen_liste = [k.strip() for k in ads_themen_input.split(",") if k.strip()]
    unternehmen = st.text_input("🏷️ Unternehmensname (für Ad-Suche)")

    combined_context = (customer_memory + "\n\n" + context).strip()

    if not combined_context and not eigene_url and not optional_pdf_path:
        st.error("❗ Kein Kontext vorhanden – bitte Text, eigene URL oder PDF angeben.")
        st.stop()
    params = {
        "task": task_id,
        "eigene_url": eigene_url,
        "wettbewerber_urls": wettbewerber_urls,
        "wettbewerber_namen": wettbewerber_namen,
        "customer_id": customer_id,
        "ads_keywords": ads_themen_liste,
        "text": combined_context,
        "customer_name": unternehmen,
        "branche": st.session_state.get("branche", ""),
        "zielgruppe": st.session_state.get("zielgruppe", "")
    }

    if facebook:
        params["facebook_company"] = unternehmen
    if google:
        params["google_company"] = unternehmen
    if linkedin:
        params["linkedin_company"] = unternehmen
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "SEO Audit":
    task_id = "seo_audit"
    combined_context = (customer_memory + "\n\n" + context).strip()
    if not combined_context and not url.strip() and not optional_pdf_path:
        st.error("❗ Bitte gib mindestens Text, URL oder PDF für die Analyse an.")
        st.stop()
    params = {
        "task": task_id,
        "text": combined_context,
        "url": url.strip(),
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "SEO Optimierung":
    task_id = "seo_optimize"

    combined_context = (customer_memory + "\n\n" + context).strip()

    if not combined_context and not url.strip() and not optional_pdf_path:
        st.error("❗ Bitte gib mindestens Text, URL oder PDF für die Optimierung an.")
        st.stop()

    params = {
        "task": task_id,
        "text": combined_context,
        "url": url.strip(),
        "customer_id": customer_id
    }

    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Technisches SEO (Lighthouse)":
    task_id = "seo_lighthouse"
    url = st.text_input("🌐 Website-URL (Pflicht)", placeholder="https://www.beispielseite.de")

    if not url.strip():
        st.error("❗ Verpflichtende URL fehlt.")
        st.stop()

    zielgruppe = st.text_input("👥 Zielgruppe (optional)", placeholder="z. B. Fachpublikum, Neukunden, KMU")
    thema = st.text_input("🧩 Fokus oder Thema der Website (optional)", placeholder="z. B. Performance, UX, Dienstleistung")
    branche = st.text_input("🏢 Branche oder Geschäftsbereich (optional)", placeholder="z. B. Agentur, Einzelhandel, SaaS")

    combined_context = (customer_memory + "\n\n" + context).strip()

    if not combined_context and not optional_pdf_path:
        st.warning("⚠️ Hinweis: Es wurde kein zusätzlicher Kontext übergeben. Nur URL wird verwendet.")

    params = {
        "task": task_id,
        "url": url.strip(),
        "zielgruppe": zielgruppe.strip(),
        "thema": thema.strip(),
        "branche": branche.strip(),
        "text": combined_context,
        "customer_id": customer_id
    }

    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Kampagnenplanung":
    task_id = "campaign_plan"

    ziel = st.text_input("🎯 Kampagnenziel")
    produkt = st.text_input("📦 Produkt/Dienstleistung")
    zeitraum = st.text_input("🕒 Zeitraum")
    zielgruppe = st.text_input("👥 Zielgruppe", placeholder="z. B. B2B Entscheider, junge Erwachsene")

    combined_context = (customer_memory + "\n\n" + context).strip()
    if not ziel.strip() and not produkt.strip() and not combined_context and not optional_pdf_path:
        st.error("❗ Bitte gib mindestens Ziel, Produkt oder Kontext an.")
        st.stop()

    params = {
        "task": task_id,
        "ziel": ziel.strip() or "Nicht angegeben",
        "produkt": produkt.strip() or "Nicht angegeben",
        "zeitraum": zeitraum.strip() or "Nicht definiert",
        "zielgruppe": zielgruppe.strip() or "Zielgruppe nicht angegeben",
        "text": combined_context,
        "customer_id": customer_id
    }

    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path


elif task == "Landingpage Strategie":
    task_id = "landingpage_strategy"

    if not url.strip():
        st.error("❗ Verpflichtende URL angeben.")
        st.stop()

    zielgruppe = st.text_input("👥 Zielgruppe")
    angebot = st.text_input("💡 Angebot")

    combined_context = (customer_memory + "\n\n" + context).strip()
    if not combined_context and not optional_pdf_path:
        st.warning("⚠️ Es wurde kein Kontexttext oder PDF übergeben – es wird nur die URL analysiert.")

    params = {
        "task": task_id,
        "zielgruppe": zielgruppe.strip() or "Zielgruppe noch nicht definiert",
        "angebot": angebot.strip() or "",
        "url": url.strip(),
        "text": combined_context,
        "customer_id": customer_id
    }

    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

    # Extra-Sicherung: sicherstellen, dass Feld existiert
    params["zielgruppe"] = params.get("zielgruppe", "Zielgruppe noch nicht definiert").strip()

elif task == "Marketingmaßnahmen planen":
    task_id = "tactical_actions"
    ziel = st.text_input("Ziel der Maßnahmen")
    zeitfenster = st.text_input("Zeitraum")

    combined_context = (customer_memory + "\n\n" + context).strip()

    # Benutzerwarnung, wenn alles leer
    if not ziel.strip() and not zeitfenster.strip() and not combined_context and not optional_pdf_path:
        st.error("❗ Bitte gib mindestens Ziel, Zeitraum oder Kontext an.")
        st.stop()

    params = {
        "task": task_id,
        "ziel": ziel.strip() or "Nicht angegeben",
        "zeitfenster": zeitfenster.strip() or "Nicht definiert",
        "text": combined_context,
        "customer_id": customer_id
    }

    # Robust: leeres Textfeld absichern
    params["text"] = params.get("text", "").strip()

    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path


elif task == "Alt-Tag Generator":
    task_id = "alt_tag_writer"

    st.markdown("🔍 Beschreibt automatisch alle Bilder einer Webseite mit SEO-relevanten Alt-Tags.")

    url = st.text_input("🌐 Website-URL (Pflicht)", placeholder="https://www.beispielseite.de")
    zielgruppe = st.text_input("👥 Zielgruppe (optional)", placeholder="z. B. Frauen 30–50, lokal interessiert")
    branche = st.text_input("🏢 Branche / Produktfeld (optional)", placeholder="z. B. Kosmetikstudio, Bäckerei, Anwaltskanzlei")
    kontexttext = st.text_area("📄 Optionaler Kontexttext oder Beschreibung", height=150)

    if not url.strip():
        st.error("❗ Bitte gib eine gültige Website-URL an.")
        st.stop()

    combined_context = (customer_memory + "\n\n" + kontexttext).strip()

    params = {
        "task": task_id,
        "url": url.strip(),
        "zielgruppe": zielgruppe.strip(),
        "branche": branche.strip(),
        "text": combined_context,
        "customer_id": customer_id
    }

    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Themen extrahieren":
    task_id = "extract_topics"

    params = {
        "task": task_id,
        "text": (customer_memory + "\n\n" + context).strip(),
        "url": url,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

    # ❗ Absicherung: mindestens eine Datenquelle muss vorhanden sein
    if not (params["text"].strip() or url or customer_id or optional_pdf_path):
        st.error("❗ Bitte gib mindestens Text, URL, Kundenkontext oder PDF an.")
        st.stop()

# -------------------------------
# Externe Datenquellen (automatisch vs. manuell)
# -------------------------------

show_sources = task in [
    "Content Analyse", "Content Writing", "Kampagnenplanung",
    "Landingpage Strategie", "SEO Optimierung",
    "Marketingmaßnahmen planen", "Wettbewerbsanalyse"
]

rss_input = trend_input = destatis_input = ""
params["use_auto_sources"] = False  # Standardwert

if show_sources:
    st.markdown("---")
    st.subheader("🌐 Themenbasierte externe Datenquellen")

    use_sources = st.checkbox("🔍 Automatische Themenvorschläge verwenden?", value=True)
    params["use_auto_sources"] = use_sources  # Nur hier setzen

    if not use_sources:
        rss_input = st.text_area("📡 RSS-Feed URLs (eine pro Zeile)", height=100)
        trend_input = st.text_input("📈 Google Trends Keywords (kommagetrennt)")
        destatis_input = st.text_input("📊 DESTATIS/Eurostat-Suchbegriffe (kommagetrennt)")

        rss_feeds_list = [u.strip() for u in rss_input.splitlines() if u.strip()]
        trend_keywords_list = [k.strip() for k in trend_input.split(",") if k.strip()]
        destatis_queries_list = [d.strip() for d in destatis_input.split(",") if d.strip()]

        if rss_feeds_list:
            params["rss_feeds"] = rss_feeds_list
        if trend_keywords_list:
            params["trend_keywords"] = trend_keywords_list
        if destatis_queries_list and task in [
            "Content Analyse", "Content Writing", "Kampagnenplanung",
            "Landingpage Strategie", "SEO Optimierung", "Monatsreport",
            "Marketingmaßnahmen planen", "Wettbewerbsanalyse"
        ]:
            params["destatis_queries"] = destatis_queries_list


# -------------------------------
# Initialer Agent-Call
# -------------------------------
clar = {}  # Initialisiere Rückfragen-Parameter

# -------------------------------
# Themenvorschlag + Bestätigung
# -------------------------------
st.warning(f"DEBUG: use_auto_sources={params.get('use_auto_sources')} | themen_bestaetigt={st.session_state.get('themen_bestaetigt')}")

if params.get("use_auto_sources") and not st.session_state.get("themen_bestaetigt"):

    st.info("🤖 Der Agent extrahiert automatisch relevante Themen für externe Datenquellen…")

    theme_text = " ".join([
        params.get("thema", ""),
        params.get("zielgruppe", ""),
        params.get("text", ""),
        customer_memory
    ])

    extract_result = run_agent(
        task="extract_topics",
        reasoning_mode=mode,
        conversation_id=None,
        clarifications={},
        text=theme_text
    )

    if not isinstance(extract_result, dict) or not isinstance(extract_result.get("response"), str):
        st.error("Agenten-Fehler: Antwort ist kein gültiges Dictionary mit String-Antwort.")
        st.write("DEBUG: extract_result:", extract_result)
        st.stop()

    proposed_topics = [line.strip("• ").strip() for line in extract_result["response"].splitlines() if line.strip()]

    st.session_state.auto_topics = proposed_topics
    st.session_state.final_topics = proposed_topics

    # Nur initial setzen – oder nach Reset
    if "editable_topics" not in st.session_state or st.session_state.get("reset_topics", False):
        st.session_state.editable_topics = "\n".join(proposed_topics)
        st.session_state.reset_topics = False

    st.markdown("### 🧠 Themenvorschlag des Agenten:")
    editable_topics = st.text_area(
        "✏️ Bearbeite oder lösche die vorgeschlagenen Themen (ein Thema pro Zeile):",
        value=st.session_state.editable_topics,
        height=150
    )

    st.session_state.editable_topics = editable_topics

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✅ Themen übernehmen und starten", key="confirm_edit"):
            user_topics = [line.strip() for line in editable_topics.splitlines() if line.strip()]
            if not user_topics:
                st.warning("Bitte gib mindestens ein Thema an.")
                st.stop()
            else:
                params["topic_keywords"] = user_topics
                st.session_state.themen_bestaetigt = True
                st.session_state.start_agent = True
                st.rerun()
    with col2:
        if st.button("🗘 Themen zurücksetzen", key="reset_topics_button"):
            st.session_state.reset_topics = True
            st.rerun()

# -------------------------------
# Manueller Start-Button: Nur wenn keine Themen vorgeschlagen oder bereits bestätigt
# -------------------------------
if not params.get("use_auto_sources") or st.session_state.get("themen_bestaetigt"):
    if "confirm_edit" not in st.session_state or not st.session_state.confirm_edit:
        if st.button("🤖 KI Agent starten", key="manual_start_button"):
            st.session_state.start_agent = True

# -------------------------------
# Initialer Agent-Call
# -------------------------------
if ((not params.get("use_auto_sources")) or st.session_state.get("themen_bestaetigt")) and st.session_state.start_agent:

    # Validierung für Tasks mit Mindestanforderungen
    required_fallback_keys = {
        "tactical_actions": ["text", "url", "customer_id"],
        "seo_optimization": ["text", "url", "customer_id"],
        "content_analysis": ["text", "url", "customer_id"],
    }
    fallback_keys = required_fallback_keys.get(task_id, [])
    if fallback_keys and not any(params.get(k) for k in fallback_keys):
        st.error(f"❗ Der Agent benötigt mindestens einen dieser Werte: {', '.join(fallback_keys)}.")
        st.stop()

    # --------------------------------
    # Mapping für lesbare Tasknamen → interne Task-IDs
    # --------------------------------
    task_map = {
        "Content Analyse": "content_analysis",
        "Content Writing": "content_writing",
        "Wettbewerbsanalyse": "competitive_analysis",
        "SEO Audit": "seo_audit",
        "SEO Optimierung": "seo_optimization",
        "Technisches SEO (Lighthouse)": "seo_lighthouse",
        "Kampagnenplanung": "campaign_plan",
        "Landingpage Strategie": "landingpage_strategy",
        "Monatsreport": "monthly_report",
        "Marketingmaßnahmen planen": "tactical_actions",
        "Alt-Tag Generator": "alt_tag_writer"
    }

    task_id = task_map.get(task)


    clar = {}  # Rückfragen-Parameter initialisieren

    # Kopiere params und entferne "task", damit kein Konflikt mit run_agent(task=...) entsteht
    params_for_agent = dict(params)
    params_for_agent.pop("task", None)

    # Robuste Initialisierung aller Felder
    params_for_agent["zielgruppe"]     = (params.get("zielgruppe") or "").strip()
    params_for_agent["branche"]        = (params.get("branche") or "").strip()
    params_for_agent["text"]           = (params.get("text") or "").strip()
    params_for_agent["context"]        = params_for_agent["text"] 
    params_for_agent["url"]            = (params.get("url") or "").strip()
    params_for_agent["thema"]          = (params.get("thema") or "").strip()
    params_for_agent["keywords"] = ", ".join(params.get("topic_keywords") or [])
    params_for_agent["topic_keywords"] = params.get("topic_keywords") or []
    params_for_agent["customer_id"]    = (params.get("customer_id") or "").strip()
    params_for_agent["ziel"]     = (params.get("ziel") or "").strip()
    params_for_agent["angebot"]  = (params.get("angebot") or "").strip()

    with st.spinner("🧠 Der Agent denkt nach…"):
        result = run_agent(
            task=task_id,
            reasoning_mode=mode,
            conversation_id=st.session_state.get("conv_id"),
            clarifications=clar,
            **params_for_agent  # enthält bereits alle nötigen Parameter
        )



        # Zwischenspeichern der Ergebnisse
        st.session_state.response = result.get("response", "")
        st.session_state.questions = result.get("questions", [])
        st.session_state.conv_id = result.get("conversation_id")
        st.session_state.themen_bestaetigt = False  # zurücksetzen für zukünftige Runs
        st.session_state.start_agent = False

    # Logging des Runs
    log_event({
        "type": "task_run",
        "customer_id": params.get("customer_id"),
        "task": task_id,
    })

    # Rückfragen initialisieren (falls vorhanden)
    for i, _ in enumerate(st.session_state.questions):
        st.session_state.setdefault(f"clar_{i}", "")

# -------------------------------
# Endgültiges Ergebnis anzeigen + Speichern
# -------------------------------
if st.session_state.response:
    st.subheader("📢 Ergebnis:")
    st.write(st.session_state.response)

    if st.button("💾 Ergebnis ins Kundengedächtnis speichern"):
        try:
            save_customer_memory(customer_id, st.session_state.response)
            st.success("✅ Ergebnis wurde erfolgreich im Kundengedächtnis gespeichert.")
        except Exception as e:
            st.error(f"❌ Fehler beim Speichern: {e}")

# -------------------------------
# Freier Folgefragen-Dialog (mehrfach möglich)
# -------------------------------
if st.session_state.response:
    st.markdown("### ❓ Weitere Frage an den Agenten")
    follow_up = st.text_area("Neue Frage eingeben", key="follow_up_text")

    if st.button("Antwort generieren", key="ask_follow_up"):
        if follow_up.strip():
            with st.spinner("⏳ Agent denkt über die Rückfrage nach…"):
                try:
                    params_for_agent = dict(params)
                    params_for_agent.pop("task", None)

                    result = run_agent(
                        task=task_id,
                        reasoning_mode=mode,
                        conversation_id=st.session_state.get("conv_id"),
                        follow_up=follow_up,
                        is_follow_up=True,
                        **params_for_agent
                    )

                    st.session_state.response += f"\n\n---\n\n➡️ **Frage:** {follow_up}\n\n🧠 **Antwort:**\n{result['response']}"
                    st.session_state.conv_id = result.get("conversation_id")

                except Exception as e:
                    st.error(f"Fehler bei der Folgefrage: {e}")



