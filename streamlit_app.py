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
    "Wettbewerbsanalyse",
    "SEO Audit",
    "SEO Optimierung",
    "Technisches SEO (Lighthouse)",
    "Kampagnenplanung",
    "Landingpage Strategie",
    "Monatsreport",
    "Marketingmaßnahmen planen"
])

url = st.text_input("🌐 (Optional) Website-URL", placeholder="https://...")

# Dynamische Eingabefelder je nach Modus
if task == "Wettbewerbsanalyse":
    col1, col2 = st.columns(2)
    with col1:
        kunde = st.text_area("👤 Kundentext", height=200)
    with col2:
        mitbewerber = st.text_area("🏢 Mitbewerbertext", height=200)

elif task == "SEO Optimierung":
    context = st.text_area("📄 Optionaler Kontext/Text", height=200)
    audit_pdf = st.file_uploader("📥 Optional: SEO Audit PDF", type="pdf")
    audit_path = None
    if audit_pdf:
        audit_path = "audit_temp.pdf"
        with open(audit_path, "wb") as f:
            f.write(audit_pdf.read())
    else:
        audit_path = None  # Wichtig: Initialisieren

elif task == "Landingpage Strategie":
    context = st.text_area("📄 Optionaler Text (wenn keine URL)", height=200)
    pdf_file = st.file_uploader("📥 Optional: Analyse-PDF (z. B. Wettbewerbsanalyse oder Kampagnenplan)", type="pdf")
    pdf_path = None
    if pdf_file:
        pdf_path = "landingpage_anhang.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.read())
    else:
        pdf_path = None

elif task == "Marketingmaßnahmen planen":
    context = st.text_area("📄 Kontext oder Text", height=200)
    measures_pdf = st.file_uploader("📥 Optional: Frühere Analyse, Audit oder Wettbewerbsanalyse (PDF)", type="pdf")
    measures_pdf_path = None
    if measures_pdf:
        measures_pdf_path = "measures_context.pdf"
        with open(measures_pdf_path, "wb") as f:
            f.write(measures_pdf.read())
    else:
        measures_pdf_path = None

elif task == "Monatsreport":
    context = st.text_area("📄 Kontext oder Text", height=200)
    report_pdf = st.file_uploader("📅 Optional: Relevante Reportings oder Analysen (PDF)", type="pdf")
    report_pdf_path = None
    if report_pdf:
        report_pdf_path = "monthly_report_input.pdf"
        with open(report_pdf_path, "wb") as f:
            f.write(report_pdf.read())
    else:
        report_pdf_path = None

else:
        report_pdf_path = None

# Button zur Ausführung
if st.button("✅ Absenden"):
    if task == "Content Briefing":
        st.write(run_agent(mode="briefing", text=context))

    elif task == "Wettbewerbsanalyse":
        if kunde and mitbewerber:
            st.write(run_agent(mode="vergleich", text_kunde=kunde, text_mitbewerber=mitbewerber))
        else:
            st.error("❗ Bitte beide Texte ausfüllen.")

    elif task == "SEO Audit":
        st.write(run_agent(mode="seo_audit", text=context, url=url))

    elif task == "SEO Optimierung":
        st.write(run_agent(mode="seo_optimize", text=context, url=url, audit_pdf_path=audit_path))

    elif task == "Technisches SEO (Lighthouse)":
        if url:
            st.write(run_agent(mode="seo_lighthouse", url=url))
        else:
            st.error("❗ Bitte eine gültige URL angeben.")

    elif task == "Kampagnenplanung":
        st.write(run_agent(mode="campaign_plan", text=context, url=url))

    elif task == "Landingpage Strategie":
        st.write(run_agent(mode="landingpage_strategy", text=context, url=url, pdf_path=pdf_path))

    elif task == "Monatsreport":
        st.write(run_agent(mode="monthly_report", text=context, url=url, audit_pdf_path=report_pdf_path))

    elif task == "Marketingmaßnahmen planen":
        st.write(run_agent(mode="tactical_actions", text=context, url=url, audit_pdf_path=measures_pdf_path))

