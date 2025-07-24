import os
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from agent import loader, embedder, vectorstore, query
from agent.base_agent import run_agent

st.set_page_config(page_title="Marketing KI-Agent", layout="wide")
st.title("🧠 Marketing KI-Agent")

# ========== PDF Upload ========== 
uploaded_file = st.file_uploader("📄 Lade eine PDF hoch", type=["pdf"])
question = st.text_input("❓ Deine Frage")

if uploaded_file:
    with open("uploaded.pdf", "wb") as f:
        f.write(uploaded_file.read())
    st.success("✅ Datei gespeichert!")

    text = loader.load_pdf("uploaded.pdf")
    chunks = []
    for para in text.split("\n\n"):
        if para.strip():
            emb = embedder.create_embedding(para)
            chunks.append({"text": para, "embedding": emb})
    vectorstore.upsert_chunks(chunks)
    st.success(f"✅ {len(chunks)} Chunks gespeichert!")

if question:
    answer = query.query_agent(question)
    st.subheader("📢 GPT-4o Antwort:")
    st.write(answer)

# ========== Intelligente Agenten-Aufgaben ========== 
st.markdown("---")
st.header("🎯 Marketing-Tasks mit KI-Agent")

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

# Gemeinsame Eingabefelder
url = st.text_input("🌐 (Optional) Website-URL", placeholder="https://...")
context = st.text_area("📄 Optionaler Kontext/Text", height=200)
optional_pdf = st.file_uploader("📥 Optional: Kontext-PDF hochladen", type="pdf")
optional_pdf_path = None
if optional_pdf:
    optional_pdf_path = "optional_context.pdf"
    with open(optional_pdf_path, "wb") as f:
        f.write(optional_pdf.read())

# Spezifische Eingabefelder
kunde = mitbewerber = eigene_url = wettbewerber_urls = audit_path = pdf_path = measures_pdf_path = report_pdf_path = None
briefing_typ = kanal = thema = zielgruppe = tonalitaet = ""

if task == "Content-Vergleich":
    kunde = st.text_area("👤 Kundentext", height=200)
    mitbewerber = st.text_area("🏢 Mitbewerbertext", height=200)

elif task == "Wettbewerbsanalyse (Webseiten)":
    eigene_url = st.text_input("🌐 Deine Website-URL", placeholder="https://www.deineseite.de")
    wettbewerber_urls = st.text_area("🏢 Wettbewerber-URLs (eine pro Zeile)", height=200)

elif task == "Content Briefing":
    briefing_typ = st.radio("Modus wählen:", ["Analyse", "Writing"])
    if briefing_typ == "Writing":
        zielgruppe = st.text_input("👥 Zielgruppe")
        tonalitaet = st.text_input("🎙️ Tonalität")
        thema = st.text_input("📝 Thema")

elif task == "Kampagnenplanung":
    thema = st.text_input("📝 Thema der Kampagne")
    kanal = st.selectbox("📢 Kanal", ["LinkedIn", "Instagram", "Blog", "E-Mail", "Facebook", "Xing"])

# Button zur Ausführung
if st.button("✅ Absenden"):
    if task == "Content Briefing":
        if briefing_typ == "Analyse":
            st.write(run_agent(mode="briefing_analysis", text=context, url=url, pdf_path=optional_pdf_path))
        else:
            if zielgruppe and tonalitaet and thema:
                st.write(run_agent(mode="briefing_write", zielgruppe=zielgruppe, tonalitaet=tonalitaet, thema=thema))
            else:
                st.error("❗ Bitte Zielgruppe, Tonalität und Thema angeben.")

    elif task == "Content-Vergleich":
        if kunde and mitbewerber:
            st.write(run_agent(mode="vergleich", text_kunde=kunde, text_mitbewerber=mitbewerber))
        else:
            st.error("❗ Bitte beide Texte ausfüllen.")

    elif task == "Wettbewerbsanalyse (Webseiten)":
        if eigene_url and wettbewerber_urls.strip():
            wettbewerber_liste = [url.strip() for url in wettbewerber_urls.strip().splitlines() if url.strip()]
            st.write(run_agent(mode="vergleich", eigene_url=eigene_url, wettbewerber_urls=wettbewerber_liste, pdf_path=optional_pdf_path))
        else:
            st.error("❗ Bitte gib deine eigene Website und mindestens eine Wettbewerber-URL an.")

    elif task == "SEO Audit":
        st.write(run_agent(mode="seo_audit", text=context, url=url, pdf_path=optional_pdf_path))

    elif task == "SEO Optimierung":
        st.write(run_agent(mode="seo_optimize", text=context, url=url, pdf_path=optional_pdf_path))

    elif task == "Technisches SEO (Lighthouse)":
        if url:
            st.write(run_agent(mode="seo_lighthouse", url=url, pdf_path=optional_pdf_path))
        else:
            st.error("❗ Bitte eine gültige URL angeben.")

    elif task == "Kampagnenplanung":
        st.write(run_agent(mode="campaign_plan", text=context, url=url, thema=thema, kanal=kanal, pdf_path=optional_pdf_path))

    elif task == "Landingpage Strategie":
        st.write(run_agent(mode="landingpage_strategy", text=context, url=url, pdf_path=optional_pdf_path))

    elif task == "Monatsreport":
        st.write(run_agent(mode="monthly_report", text=context, url=url, pdf_path=optional_pdf_path))

    elif task == "Marketingmaßnahmen planen":
        st.write(run_agent(mode="tactical_actions", text=context, url=url, pdf_path=optional_pdf_path))
