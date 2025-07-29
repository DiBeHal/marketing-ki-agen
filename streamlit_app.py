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
for key in ('last_task', 'last_mode', 'conv_id', 'questions', 'response'):
    if key not in st.session_state:
        st.session_state[key] = None if key in ('last_task','last_mode','conv_id') else []

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
        df['timestamp'] = pd.to_datetime(df['timestamp'])

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
        pivot = usage_grp.pivot(index='customer_id', columns='mode', values='cost').fillna(0)
        st.bar_chart(pivot)
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
            st.write("Token Usage", usage[usage["customer_id"] == cid][['mode','input_tokens','output_tokens','timestamp']])
            st.write("Feedback", feedback[feedback["customer_id"] == cid][['rating','comment','timestamp']])
            st.write("Rohes Log", df[df["customer_id"] == cid])

    st.stop()

# ===============================  
# User-Tasks  
# ===============================
st.title("👤 Kunden-Upload & KI-Agent")

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

# Mode- & Task-Auswahl
mode_label = st.radio("Modus wählen:", ["⚡ Schnell", "🧠 Tiefenanalyse"], horizontal=True)
mode = "fast" if mode_label == "⚡ Schnell" else "deep"

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
    "Monatsreport",
    "Marketingmaßnahmen planen"
])

# Reset bei Task- oder Modus-Wechsel
if task != st.session_state.last_task or mode != st.session_state.last_mode:
    st.session_state.conv_id = None
    st.session_state.questions = []
    st.session_state.response = ""
    st.session_state.last_task = task
    st.session_state.last_mode = mode

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
    if not (context or url):
        st.error("❗ Bitte Kontexttext oder URL angeben.")
        st.stop()
    params = {
        "task": task_id,
        "text": customer_memory + "\n\n" + context,
        "url": url,
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
    wettbewerber = st.text_area("🏢 Wettbewerber-URLs (eine pro Zeile)", height=200)
    wettbewerber_urls = [url.strip() for url in wettbewerber.split("\n") if url.strip()]
    if not (eigene_url and wettbewerber_urls):
        st.error("❗ Bitte eigene URL und Wettbewerber-URLs angeben.")
        st.stop()

    st.subheader("📊 Optional: Werbebibliotheken einbeziehen")
    facebook = st.checkbox("📘 Facebook Ads Library einbeziehen?")
    google = st.checkbox("🔍 Google Ads Transparency Center einbeziehen?")
    linkedin = st.checkbox("💼 LinkedIn Ads Library einbeziehen?")

    ads_themen_input = st.text_input("🔎 Themen/Produkte für Werbeanalyse (kommagetrennt)")
    ads_themen_liste = [k.strip() for k in ads_themen_input.split(",") if k.strip()]
    unternehmen = st.text_input("🏷️ Unternehmensname (für Ad-Suche)")

    params = {
        "task": task_id,
        "eigene_url": eigene_url,
        "wettbewerber_urls": wettbewerber_urls,
        "customer_id": customer_id,
        "ads_keywords": ads_themen_liste,
        "text": customer_memory + "\n\n" + context,
        "customer_name": unternehmen
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
    params = {
        "task": task_id,
        "url": url,
        "text": customer_memory + "\n\n" + context,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "SEO Optimierung":
    task_id = "seo_optimization"
    params = {
        "task": task_id,
        "text": customer_memory + "\n\n" + context,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Technisches SEO (Lighthouse)":
    task_id = "seo_lighthouse"
    if not url:
        st.error("❗ Verpflichtende URL angeben.")
        st.stop()
    params = {
        "task": task_id,
        "url": url,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Kampagnenplanung":
    task_id = "campaign_plan"
    ziel = st.text_input("🎯 Kampagnenziel")
    produkt = st.text_input("📦 Produkt/Dienstleistung")
    zeitraum = st.text_input("🕒 Zeitraum")
    params = {
        "task": task_id,
        "ziel": ziel,
        "produkt": produkt,
        "zeitraum": zeitraum,
        "text": customer_memory + "\n\n" + context,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Landingpage Strategie":
    task_id = "landingpage_strategy"
    if not url:
        st.error("❗ Verpflichtende URL angeben.")
        st.stop()
    zielgruppe = st.text_input("👥 Zielgruppe")
    angebot = st.text_input("💡 Angebot")
    params = {
        "task": task_id,
        "zielgruppe": zielgruppe,
        "angebot": angebot,
        "url": url,
        "text": customer_memory + "\n\n" + context,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Monatsreport":
    task_id = "monthly_report"
    monat = st.text_input("📆 Monat (z. B. 2024-07)")
    params = {
        "task": task_id,
        "monat": monat,
        "text": customer_memory + "\n\n" + context,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

elif task == "Marketingmaßnahmen planen":
    task_id = "tactical_actions"
    ziel = st.text_input("🎯 Ziel")
    zeitfenster = st.text_input("🗓️ Zeitraum")
    params = {
        "task": task_id,
        "ziel": ziel,
        "zeitfenster": zeitfenster,
        "text": customer_memory + "\n\n" + context,
        "customer_id": customer_id
    }
    if optional_pdf_path:
        params["pdf_path"] = optional_pdf_path

# -------------------------------
# Externe Datenquellen (automatisch vs. manuell)
# -------------------------------

show_sources = (
    mode == "deep" or (mode == "fast" and task == "Content Writing")
)
use_sources = False
rss_input = trend_input = destatis_input = ""

if show_sources:
    st.markdown("---")
    st.subheader("🌐 Themenbasierte externe Datenquellen")
    use_sources = st.checkbox("🔍 Automatische Themenvorschläge verwenden?", value=True)

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
    else:
        params["use_auto_sources"] = True

# -------------------------------
# Initialer Agent-Call
# -------------------------------
clar = {}  # Initialisiere Rückfragen-Parameter

# -------------------------------
# Themenvorschlag + Bestätigung
# -------------------------------
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

    suggested_topics_raw = extract_result["response"]
    proposed_topics = [line.strip("• ").strip() for line in suggested_topics_raw.splitlines() if line.strip()]
    st.session_state.auto_topics = proposed_topics
    st.session_state.final_topics = proposed_topics  # Default, falls keine Bearbeitung erfolgt

    st.markdown("### 🧠 Themenvorschlag des Agenten:")
    editable_topics = st.text_area(
        "✏️ Bearbeite oder lösche die vorgeschlagenen Themen (ein Thema pro Zeile):",
        value="\n".join(proposed_topics),
        height=150,
        key="editable_topics"
    )

    if st.button("✅ Themen übernehmen und starten", key="confirm_edit"):
        user_topics = [line.strip() for line in editable_topics.splitlines() if line.strip()]
        if not user_topics:
            st.warning("Bitte gib mindestens ein Thema an.")
            st.stop()
        params["topic_keywords"] = user_topics
        st.session_state.themen_bestaetigt = True
        st.rerun()


# -------------------------------
# Initialer Agent-Call
# -------------------------------
if (not params.get("use_auto_sources")) or st.session_state.get("themen_bestaetigt"):
    clar = {}  # Initialisiere Rückfragen-Parameter
    with st.spinner("🧠 Der Agent denkt nach…"):
        result = run_agent(
            task=task_id, 
            reasoning_mode=mode,
            conversation_id=st.session_state.conv_id,
            clarifications=clar,
            **params
        )

        st.session_state.response = result["response"]
        st.session_state.questions = result.get("questions", [])
        st.session_state.conv_id = result.get("conversation_id")
        st.session_state.themen_bestaetigt = False  # zurücksetzen nach Analyse

    log_event({
        "type": "task_run",
        "customer_id": params.get("customer_id"),
        "task": task_id,
        "mode": mode
    })

    for i in range(len(st.session_state.questions)):
        key = f"clar_{i}"
        if key not in st.session_state:
            st.session_state[key] = ""

# -------------------------------
# Rückfragen-Loop (Deep-Modus)
# -------------------------------
while st.session_state.questions:
    st.markdown("### 🤔 Rückfragen des Agenten (Deep-Modus):")
    clarifications = {}

    for i, question in enumerate(st.session_state.questions):
        clarifications[question] = st.text_input(f"🔁 Rückfrage {i+1}: {question}", key=f"clar_{i}")

    if st.button("📝 Rückfragen beantworten"):
        with st.spinner("🔄 Rückfragen werden verarbeitet…"):
            try:
                follow_up_result = run_agent(
                    task=task_id,
                    reasoning_mode=mode,
                    conversation_id=st.session_state.conv_id,
                    clarifications=clarifications,
                    **params
                )

                st.session_state.response = follow_up_result["response"]
                st.session_state.questions = follow_up_result.get("questions", [])
                st.session_state.conv_id = follow_up_result.get("conversation_id")

            except Exception as e:
                st.error(f"Fehler bei der Rückfragenverarbeitung: {e}")
            st.experimental_rerun()
    else:
        st.stop()


# -------------------------------
# Endgültiges Ergebnis anzeigen
# -------------------------------
if not st.session_state.questions and st.session_state.response:
    st.subheader("📢 Ergebnis:")
    st.write(st.session_state.response)

    rating = st.slider("Wie hilfreich war das Ergebnis? (1–10)", 1, 10, 7)
    comment = st.text_area("📝 Dein Feedback (optional)")
    if st.button("✅ Feedback speichern"):
        if selected_customer != "– Kein Kunde –":
            log_event({
                "type": "rating",
                "customer_id": selected_customer,
                "rating": rating,
                "comment": comment
            })
            if rating >= 7:
                save_customer_memory(selected_customer, st.session_state.response)
                st.success("✅ Ergebnis im Kundengedächtnis gespeichert.")
            else:
                st.info("📩 Feedback gespeichert.")
        else:
            st.error("❗ Kein Kunde ausgewählt – Feedback wurde nicht gespeichert.")

# -------------------------------
# Rückfrage-Dialog (manuell)
# -------------------------------
if st.session_state.response:
    st.markdown("### 💬 Rückfrage stellen")
    follow_up = st.text_input("❓ Weitere Frage an den Agenten", key="follow_up")

    if follow_up:
        with st.spinner("⏳ Agent denkt über die Rückfrage nach…"):
            try:
                follow_up_result = run_agent(
                    task=task_id,
                    reasoning_mode=mode,
                    conversation_id=st.session_state.conv_id,
                    follow_up=follow_up,
                    is_follow_up=True,
                    **params
                )

                st.session_state.response += "\n\n**Antwort auf Rückfrage:**\n" + follow_up_result["response"]
                st.session_state.questions.append(follow_up)
                st.markdown(follow_up_result["response"])

            except Exception as e:
                st.error(f"❌ Fehler bei der Rückfrage: {e}")
