import streamlit as st
import os
import random
import string

from agent.customer_memory import (
    save_customer_data,
    list_customer_ids,
    load_customer_memory,
    save_customer_memory
)
from agent.loader import load_pdf
from agent.base_agent import run_agent

st.set_page_config(page_title="Kunden-Upload & KI-Agent", layout="wide")
st.title("👤 Kunden-Upload")

# ===== Session-State für Deep-Loop persistieren =====
if 'last_task' not in st.session_state:
    st.session_state.last_task = None
if 'last_mode' not in st.session_state:
    st.session_state.last_mode = None
if 'conv_id' not in st.session_state:
    st.session_state.conv_id = None
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'response' not in st.session_state:
    st.session_state.response = ""
# Klarstellungen werden dynamisch über eigene Keys gespeichert

# -------------------------------
# Kundenprofil anlegen
# -------------------------------
customer_name = st.text_input("Name des neuen Kunden (z. B. Kosmetikstudio Müller)")
url_input = st.text_input("Website-URL des Kunden")
pdf_file = st.file_uploader("Optional: PDF-Datei mit Informationen zum Kunden", type=["pdf"])
notes = st.text_area("Optional: Weitere Informationen zum Kunden")

if st.button("✅ Kundenprofil erstellen"):
    if not customer_name or not url_input:
        st.error("Bitte gib mindestens den Kundennamen und eine Website-URL an.")
    else:
        identifier = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        pdf_text = load_pdf(pdf_file) if pdf_file else ""
        data = {"name": customer_name, "url": url_input, "pdf": pdf_text, "notes": notes}
        save_customer_data(identifier, data)
        st.success(f"Kundenprofil erfolgreich erstellt. ID: {identifier}")
        st.info("Der Agent verwendet diese Daten ab sofort für Analysen, wenn du diesen Kunden auswählst.")

# ===============================
# KI-Agent mit Deep vs. Fast Mode
# ===============================
st.markdown("---")
st.header("🎯 Marketing-Tasks mit KI-Agent")

# Mode-Auswahl
mode_label = st.radio("Modus wählen:", ["⚡ Schnell", "🧠 Tiefenanalyse"], horizontal=True)
mode = "fast" if mode_label == "⚡ Schnell" else "deep"

# Task-Auswahl
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

# Reset, wenn Task oder Modus gewechselt
if task != st.session_state.last_task or mode != st.session_state.last_mode:
    st.session_state.conv_id = None
    st.session_state.questions = []
    st.session_state.response = ""
    st.session_state.last_task = task
    st.session_state.last_mode = mode

# Kundenkontext laden
customer_options = ["– Kein Kunde –"] + list_customer_ids()
selected_customer = st.selectbox("🧠 Ordne Analyse optional einem Kunden zu:", customer_options)

customer_memory = ""
if selected_customer != "– Kein Kunde –":
    customer_memory = load_customer_memory(selected_customer)
    if customer_memory:
        st.info("🧠 Kontext aus Kundengedächtnis wird verwendet.")

# Gemeinsame Inputs
url = st.text_input("🌐 (Optional) Website-URL", placeholder="https://...")
context = st.text_area("📄 Optionaler Kontext/Text", height=200)
optional_pdf = st.file_uploader("📥 Optional: Kontext-PDF hochladen", type="pdf")
optional_pdf_path = None
if optional_pdf:
    optional_pdf_path = "optional_context.pdf"
    with open(optional_pdf_path, "wb") as f:
        f.write(optional_pdf.read())

# Task-spezifische Inputs
kunde = mitbewerber = eigene_url = wettbewerber_urls = None
briefing_typ = kanal = thema = zielgruppe = tonalitaet = ""

if task == "Content-Vergleich":
    kunde = st.text_area("👤 Kundentext", height=200)
    mitbewerber = st.text_area("🏢 Mitbewerbertext", height=200)

elif task == "Wettbewerbsanalyse (Webseiten)":
    eigene_url = st.text_input("🌐 Deine Website-URL", placeholder="https://www.deineseite.de")
    wettbewerber_urls = st.text_area("🏢 Wettbewerber-URLs (eine pro Zeile)", height=200)

elif task == "Content Briefing":
    briefing_typ = st.radio("Briefing-Modus wählen:", ["Analyse", "Writing"])
    if briefing_typ == "Writing":
        zielgruppe = st.text_input("👥 Zielgruppe")
        tonalitaet = st.text_input("🎙️ Tonalität")
        thema = st.text_input("📝 Thema")

elif task == "Kampagnenplanung":
    thema = st.text_input("📝 Thema der Kampagne")
    kanal = st.selectbox("📢 Kanal", ["LinkedIn", "Instagram", "Blog", "E-Mail", "Facebook", "Xing"])

# -------------------------------
# Initialer Agent-Call
# -------------------------------
if st.button("✅ Absenden"):
    # Parameter für run_agent sammeln
    params = {"customer_id": selected_customer if selected_customer != "– Kein Kunde –" else None}

    if task == "Content Briefing":
        if briefing_typ == "Analyse":
            params.update({
                "text": customer_memory + "\n\n" + context,
                "url": url,
                "pdf_path": optional_pdf_path
            })
            task_id = "briefing_analysis"
        else:
            if not (zielgruppe and tonalitaet and thema):
                st.error("❗ Bitte Zielgruppe, Tonalität und Thema angeben.")
                st.stop()
            params.update({
                "zielgruppe": zielgruppe,
                "tonalitaet": tonalitaet,
                "thema": thema
            })
            task_id = "briefing_write"

    elif task == "Content-Vergleich":
        if not (kunde and mitbewerber):
            st.error("❗ Bitte beide Texte ausfüllen.")
            st.stop()
        params.update({"text_kunde": kunde, "text_mitbewerber": mitbewerber})
        task_id = "vergleich"

    elif task == "Wettbewerbsanalyse (Webseiten)":
        if not (eigene_url and wettbewerber_urls.strip()):
            st.error("❗ Bitte gib deine eigene Website und mindestens eine Wettbewerber-URL an.")
            st.stop()
        params.update({
            "eigene_url": eigene_url,
            "wettbewerber_urls": [u.strip() for u in wettbewerber_urls.splitlines() if u.strip()],
            "pdf_path": optional_pdf_path
        })
        task_id = "vergleich"

    elif task == "SEO Audit":
        params.update({
            "text": customer_memory + "\n\n" + context,
            "url": url,
            "pdf_path": optional_pdf_path
        })
        task_id = "seo_audit"

    elif task == "SEO Optimierung":
        params.update({
            "text": customer_memory + "\n\n" + context,
            "url": url,
            "audit_pdf_path": optional_pdf_path
        })
        task_id = "seo_optimize"

    elif task == "Technisches SEO (Lighthouse)":
        if not url:
            st.error("❗ Bitte eine gültige URL angeben.")
            st.stop()
        params.update({"url": url})
        task_id = "seo_lighthouse"

    elif task == "Kampagnenplanung":
        params.update({
            "text": customer_memory + "\n\n" + context,
            "url": url,
            "thema": thema,
            "kanal": kanal,
            "pdf_path": optional_pdf_path
        })
        task_id = "campaign_plan"

    elif task == "Landingpage Strategie":
        params.update({
            "text": customer_memory + "\n\n" + context,
            "url": url,
            "pdf_path": optional_pdf_path
        })
        task_id = "landingpage_strategy"

    elif task == "Monatsreport":
        params.update({
            "text": customer_memory + "\n\n" + context,
            "url": url,
            "audit_pdf_path": optional_pdf_path
        })
        task_id = "monthly_report"

    elif task == "Marketingmaßnahmen planen":
        params.update({
            "text": customer_memory + "\n\n" + context,
            "url": url,
            "audit_pdf_path": optional_pdf_path
        })
        task_id = "tactical_actions"

    else:
        st.stop()

    # Agent-Call (ohne Klarstellungen)
    result = run_agent(
        task=task_id,
        reasoning_mode=mode,
        conversation_id=st.session_state.conv_id,
        clarifications=None,
        **params
    )
    st.session_state.response = result["response"]
    st.session_state.questions = result["questions"]
    st.session_state.conv_id = result["conversation_id"]

    # Klarfrage-Inputs vorbereiten
    for i, _ in enumerate(st.session_state.questions):
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
        clar_dict = {
            q: st.session_state[f"clar_{i}"]
            for i, q in enumerate(st.session_state.questions)
        }
        # Agenten-Call mit Klarstellungen
        result = run_agent(
            task=task_id,
            reasoning_mode=mode,
            conversation_id=st.session_state.conv_id,
            clarifications=clar_dict,
            **params
        )
        st.session_state.response = result["response"]
        st.session_state.questions = result["questions"]
        st.session_state.conv_id = result["conversation_id"]

        # Neue Klarfrage-Felder initialisieren
        for i, _ in enumerate(st.session_state.questions):
            key = f"clar_{i}"
            st.session_state[key] = ""

# -------------------------------
# Endgültiges Ergebnis anzeigen
# -------------------------------
if not st.session_state.questions and st.session_state.response:
    st.subheader("📢 Ergebnis:")
    st.write(st.session_state.response)

    rating = st.slider(
        "Wie hilfreich war das Ergebnis? (1 = schlecht, 10 = exzellent)",
        1, 10, 7
    )
    if selected_customer != "– Kein Kunde –" and rating >= 7:
        save_customer_memory(selected_customer, st.session_state.response)
        st.success("✅ Ergebnis im Kundengedächtnis gespeichert.")
