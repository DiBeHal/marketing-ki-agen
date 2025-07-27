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
    "Content Briefing",
    "Content-Vergleich",
    "Wettbewerbsanalyse (Webseiten)",
    "SEO Audit",
    "SEO Optimierung",
    "Technisches SEO (Lighthouse)",
    "Kampagnenplanung",
    "Landingpage Strategie",
    "Monatsreport",
    "Marketingmaßnahmen planen"
])

# Reset Deep-Loop
if task != st.session_state.last_task or mode != st.session_state.last_mode:
    st.session_state.conv_id    = None
    st.session_state.questions  = []
    st.session_state.response   = ""
    st.session_state.last_task  = task
    st.session_state.last_mode  = mode

# Kundenkontext laden
customer_options  = ["– Kein Kunde –"] + list_customer_ids()
selected_customer = st.selectbox("🧠 Ordne Analyse optional einem Kunden zu:", customer_options)
customer_memory   = load_customer_memory(selected_customer) if selected_customer != "– Kein Kunde –" else ""

# Gemeinsame Inputs
url               = st.text_input("🌐 (Optional) Website-URL", placeholder="https://…")
context           = st.text_area("📄 Optionaler Kontext/Text", height=200)
optional_pdf      = st.file_uploader("📥 Optional: Kontext-PDF hochladen", type=["pdf"])
optional_pdf_path = None
if optional_pdf:
    optional_pdf_path = "optional_context.pdf"
    with open(optional_pdf_path, "wb") as f:
        f.write(optional_pdf.read())

# Task-spezifische Inputs
kunde = mitbewerber = eigene_url = wettbewerber_urls = None
briefing_typ = kanal = thema = zielgruppe = tonalitaet = ""

if task == "Content-Vergleich":
    kunde       = st.text_area("👤 Kundentext", height=200)
    mitbewerber = st.text_area("🏢 Mitbewerbertext", height=200)

elif task == "Wettbewerbsanalyse (Webseiten)":
    eigene_url        = st.text_input("🌐 Deine Website-URL", placeholder="https://…")
    wettbewerber_urls = st.text_area("🏢 Wettbewerber-URLs (eine pro Zeile)", height=200)

elif task == "Content Briefing":
    briefing_typ = st.radio("Briefing-Modus wählen:", ["Analyse", "Writing"])
    if briefing_typ == "Writing":
        zielgruppe = st.text_input("👥 Zielgruppe")
        tonalitaet = st.text_input("🎙️ Tonalität")
        thema      = st.text_input("📝 Thema")

elif task == "Kampagnenplanung":
    thema = st.text_input("📝 Thema der Kampagne")
    kanal = st.selectbox("📢 Kanal", ["LinkedIn", "Instagram", "Blog", "E-Mail", "Facebook", "Xing"])

# -------------------------------  
# Externe Datenquellen (nur Deep-Modus)  
# -------------------------------
if mode == "deep":
    st.markdown("---")
    st.subheader("🌐 Externe Datenquellen (Deep-Modus)")
    rss_input      = st.text_area("RSS-Feed URLs (eine pro Zeile)", height=100)
    trend_input    = st.text_input("Trend-Keywords (kommagetrennt)")
    destatis_input = st.text_input("DESTATIS/Eurostat-Codes (kommagetrennt)")

    st.markdown("### 📣 Ads-Bibliotheken (Deep-Modus)")
    linkedin_input = st.text_input("LinkedIn Company Domain (z. B. unternehmensdomain.de)")
    google_input   = st.text_input("Google Ads Search Term")
    facebook_input = st.text_input("Facebook Page ID")
else:
    rss_input = trend_input = destatis_input = ""
    linkedin_input = google_input = facebook_input = ""

# -------------------------------  
# Initialer Agent-Call  
# -------------------------------
if st.button("✅ Absenden"):
    # Parse Deep-Inputs
    rss_feeds_list        = [u.strip() for u in rss_input.splitlines() if u.strip()]
    trend_keywords_list   = [k.strip() for k in trend_input.split(",") if k.strip()]
    destatis_queries_list = [c.strip() for c in destatis_input.split(",") if c.strip()]

    # Basis-Parameter
    params = {
        "customer_id": selected_customer if selected_customer != "– Kein Kunde –" else None,
        "rss_feeds": rss_feeds_list,
        "trend_keywords": trend_keywords_list,
        "destatis_queries": destatis_queries_list,
        "linkedin_company": linkedin_input,
        "google_company": google_input,
        "facebook_page": facebook_input
    }

    # Task-spezifische Parameter und Task-ID
    if task == "Content Briefing":
        if briefing_typ == "Analyse":
            params.update({
                "text": customer_memory + "\n\n" + context,
                "url": url,
                "pdf_path": optional_pdf_path
            })
            task_id = "content_analysis"
        else:
            if not (zielgruppe and tonalitaet and thema):
                st.error("❗ Bitte Zielgruppe, Tonalität und Thema angeben.")
                st.stop()
            params.update({"zielgruppe": zielgruppe, "tonalitaet": tonalitaet, "thema": thema})
            task_id = "briefing_write"

    elif task == "Content-Vergleich":
        if not (kunde and mitbewerber):
            st.error("❗ Bitte beide Texte ausfüllen.")
            st.stop()
        params.update({"text_kunde": kunde, "text_mitbewerber": mitbewerber})
        task_id = "vergleich"

    elif task == "Wettbewerbsanalyse (Webseiten)":
        if not (eigene_url and wettbewerber_urls.strip()):
            st.error("❗ Bitte eigene URL und Wettbewerber-URLs angeben.")
            st.stop()
        params.update({
            "eigene_url": eigene_url,
            "wettbewerber_urls": [u.strip() for u in wettbewerber_urls.splitlines() if u.strip()]
        })
        task_id = "vergleich"

    elif task == "SEO Audit":
        params.update({"text": customer_memory + "\n\n" + context, "url": url})
        task_id = "seo_audit"

    elif task == "SEO Optimierung":
        params.update({"text": customer_memory + "\n\n" + context, "url": url, "audit_pdf_path": optional_pdf_path})
        task_id = "seo_optimize"

    elif task == "Technisches SEO (Lighthouse)":
        if not url:
            st.error("❗ Verpflichtende URL angeben.")
            st.stop()
        params.update({"url": url})
        task_id = "seo_lighthouse"

    elif task == "Kampagnenplanung":
        params.update({"text": customer_memory + "\n\n" + context, "url": url, "thema": thema, "kanal": kanal})
        task_id = "campaign_plan"

    elif task == "Landingpage Strategie":
        if not url:
            st.error("❗ Verpflichtende URL angeben.")
            st.stop()
        params.update({"url": url})
        task_id = "landingpage_strategy"

    elif task == "Monatsreport":
        params.update({"text": customer_memory + "\n\n" + context, "url": url})
        task_id = "monthly_report"

    elif task == "Marketingmaßnahmen planen":
        params.update({"text": customer_memory + "\n\n" + context, "url": url})
        task_id = "tactical_actions"

    else:
        st.stop()

    # Aufruf des Agents
    result = run_agent(
        task=task_id,
        reasoning_mode=mode,
        conversation_id=st.session_state.conv_id,
        clarifications=None,
        **params
    )
    st.session_state.response  = result["response"]
    st.session_state.questions = result["questions"]
    st.session_state.conv_id    = result["conversation_id"]

    log_event({
        "type": "task_run",
        "customer_id": params.get("customer_id"),
        "task": task_id,
        "mode": mode
    })

    # Initialisiere Rückfragen-Felder
    for i in range(len(st.session_state.questions)):
        key = f"clar_{i}"
        if key not in st.session_state:
            st.session_state[key] = ""

# -------------------------------  
# Rückfragen-Handling (Deep-Modus)  
# -------------------------------
if mode == "deep" and st.session_state.questions:
    st.markdown("### 🤔 Rückfragen des Modells:")
    for i, q in enumerate(st.session_state.questions):
        st.text_input(label=q, key=f"clar_{i}")

    if st.button("📝 Rückfragen beantworten"):
        clar = {
            q: st.session_state[f"clar_{i}"]
            for i, q in enumerate(st.session_state.questions)
        }
        result = run_agent(
            task=task_id,
            reasoning_mode=mode,
            conversation_id=st.session_state.conv_id,
            clarifications=clar,
            **params
        )
        st.session_state.response  = result["response"]
        st.session_state.questions = result["questions"]
        st.session_state.conv_id    = result["conversation_id"]
        for i in range(len(st.session_state.questions)):
            st.session_state[f"clar_{i}"] = ""

# -------------------------------  
# Endgültiges Ergebnis anzeigen  
# -------------------------------
if not st.session_state.questions and st.session_state.response:
    st.subheader("📢 Ergebnis:")
    st.write(st.session_state.response)

    rating = st.slider("Wie hilfreich war das Ergebnis? (1–10)", 1, 10, 7)
    comment = st.text_area("Dein Feedback (optional)")
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
                st.info("Feedback gespeichert.")
        else:
            st.error("Kein Kunde ausgewählt; Feedback nicht gespeichert.")
