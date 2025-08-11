# streamlit_app.py — v4 (Merger‑first, interaktive Quellen, ohne Notion/Drive)
#
# Änderungen ggü. v3:
# - Notion/GDrive entfernt (UI + Param-Felder)
# - Task "Marketingmaßnahmen planen" (tactical_actions) hinzugefügt
# - Ergebnis: "💾 Ergebnis ins Kundengedächtnis speichern" + einfache Memory-Suche
# - Kleine Robustheit (Defaults, Fehlertexte)

import os
import hashlib
from dotenv import load_dotenv

import streamlit as st
import random
import string
import pandas as pd
from collections import Counter

from agent.context_merger import ContextMerger
from agent.customer_memory import (
    save_customer_data,
    list_customer_ids,
    load_customer_memory,
    save_customer_memory,
)
from agent.loader import load_pdf
from agent.activity_log import (
    load_events_as_dataframe,
    log_event,
)
from agent.base_agent import run_agent

load_dotenv()

# -----------------------------------------------------------------------------
# Auth
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
    st.title("🔐 Login")
    user = st.text_input("Benutzername")
    pwd  = st.text_input("Passwort", type="password")
    if st.button("Anmelden"):
        if check_credentials(user, pwd):
            st.session_state.authenticated = True
        else:
            st.error("Ungültige Anmeldedaten")
    st.stop()

# -----------------------------------------------------------------------------
# Layout
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Kunden-Upload & KI-Agent", layout="wide")

if 'context_plan' not in st.session_state:
    st.session_state.context_plan = {}
if 'context_bundle' not in st.session_state:
    st.session_state.context_bundle = {}
if 'proposed_sources' not in st.session_state:
    st.session_state.proposed_sources = []
if 'selected_sources' not in st.session_state:
    st.session_state.selected_sources = []
if 'source_params' not in st.session_state:
    st.session_state.source_params = {}
if 'conv_id' not in st.session_state:
    st.session_state.conv_id = None

page = st.sidebar.selectbox("Ansicht wählen:", ["🎯 User-Tasks", "⚙️ Admin-Dashboard"]) 

# ===============================
# Admin
# ===============================
if page == "⚙️ Admin-Dashboard":
    st.title("⚙️ Admin-Dashboard")
    try:
        df = load_events_as_dataframe()
    except Exception:
        df = pd.DataFrame(columns=["type","timestamp","customer_id","task","rating","comment","mode","input_tokens","output_tokens"]) 

    st.subheader("🔹 Kunden-Übersicht")
    if not df.empty:
        customers = sorted(set(df[df["customer_id"].notna()]["customer_id"]))
        tasks_df = df[df["type"] == "task_run"]
        feedback = df[df["type"] == "rating"]
        usage   = df[df["type"] == "usage"]

        st.write("Anzahl Kunden:", len(customers))
        words = Counter()
        if not feedback.empty:
            for c in feedback["comment"].dropna().astype(str):
                for w in c.lower().split():
                    words[w] += 1
            st.write("Top 5 Feedback-Begriffe:", words.most_common(5))
        else:
            st.info("Noch kein Feedback vorhanden.")

        st.subheader("🔍 Details pro Kunde")
        for cid in customers:
            with st.expander(f"Kunde {cid}"):
                st.write("Letzte Tasks", tasks_df[tasks_df["customer_id"] == cid][['task','timestamp']])
                st.write("Token Usage", usage[usage["customer_id"] == cid][['input_tokens','output_tokens','timestamp']])
                st.write("Feedback", feedback[feedback["customer_id"] == cid][['rating','comment','timestamp']])
                st.write("Rohes Log", df[df["customer_id"] == cid])
    else:
        st.info("Noch keine Events vorhanden.")
    st.stop()

# ===============================
# User-Tasks
# ===============================
st.title("👤 Kunden-Upload & KI-Agent")

# Kundenprofil
customer_name = st.text_input("Name des neuen Kunden")
url_input     = st.text_input("Website-URL des Kunden")
pdf_file      = st.file_uploader("Optional: PDF-Datei", type=["pdf"])
notes         = st.text_area("Optionale Notizen")

if st.button("✅ Kundenprofil erstellen"):
    if not customer_name or not url_input:
        st.error("Bitte Kundennamen und Website-URL angeben.")
    else:
        identifier = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        pdf_text = load_pdf(pdf_file) if pdf_file else ""
        save_customer_data(identifier, {"name": customer_name,"url": url_input,"pdf": pdf_text,"notes": notes})
        st.success(f"Kundenprofil erstellt. ID: {identifier}")

st.subheader("🧠 Kontextplanung (Schritt 1)")

# Task-Auswahl
task_options = {
    "–": "Bitte wählen",
    "Content Analyse": "content_analysis",
    "Content Writing": "content_writing",
    "Wettbewerbsanalyse": "competitive_analysis",
    "SEO Audit": "seo_audit",
    "SEO Optimierung": "seo_optimization",
    "Technisches SEO (Lighthouse)": "seo_lighthouse",
    "Kampagnenplanung": "campaign_plan",
    "Landingpage Strategie": "landingpage_strategy",
    "Alt-Tag Generator": "alt_tag_writer",
    "Marketingmaßnahmen planen": "tactical_actions",
}

ui_task = st.selectbox("Wähle Task", list(task_options.keys()))
selected_task = task_options.get(ui_task)

# Freie Felder
col1, col2, col3 = st.columns(3)
with col1:
    zielgruppe = st.text_input("Zielgruppe")
    tonalitaet = st.text_input("Tonalität")
with col2:
    thema = st.text_input("Thema / Fokus")
    keyword_fokus = st.text_input("Keyword-Fokus")
with col3:
    plattform = st.text_input("Plattform")
    produktname = st.text_input("Produktname")

gliederungspunkte = st.text_area("Gewünschte Gliederungspunkte")
formatwunsch = st.text_input("Gewünschtes Format")

query = st.text_area("Beschreibe dein Ziel / deine Frage")

if st.button("🔍 Vorschläge & Plan anzeigen"):
    merger = ContextMerger(
        query=query,
        task=selected_task,
        url=url_input,
        customer_id=customer_name,
        pdf_path=None,
        fields={
            "zielgruppe": zielgruppe,
            "thema": thema,
            "tonalitaet": tonalitaet,
            "keyword_fokus": keyword_fokus,
            "plattform": plattform,
            "produktname": produktname,
            "gliederungspunkte": gliederungspunkte,
            "formatwunsch": formatwunsch,
        }
    )
    plan = merger.reason_before_merge()
    st.session_state.context_plan = plan.get("plan", {})
    # Notion/GDrive filtern, falls der Merger sie noch vorschlägt
    proposed = [s for s in plan.get("proposed_sources", []) if s.get("id") not in {"notion","gdrive"}]
    st.session_state.proposed_sources = proposed
    st.success("Plan erstellt. Wähle nun die Quellen unten aus und bestätige.")

# Plan-Preview
with st.expander("🧭 Kontext-Plan (raw)"):
    st.json(st.session_state.get("context_plan", {}))

# Schritt 2: Quellen-Auswahl
st.subheader("📦 Quellen auswählen (Schritt 2)")
proposed = st.session_state.get("proposed_sources", [])
if not proposed:
    st.info("Noch keine vorgeschlagenen Quellen. Erzeuge zuerst den Plan oben.")
else:
    chosen_ids = []
    src_params = {}
    cols = st.columns(2)
    for i, s in enumerate(proposed):
        with cols[i % 2]:
            default = bool(s.get("default"))
            checked = st.checkbox(f"{s['label']} ({s['id']})", value=default, key=f"src_{s['id']}")
            st.caption(s.get("reason", ""))
            if checked:
                chosen_ids.append(s['id'])
                # Per-Quelle Parameter
                if s['id'] == 'rss':
                    feeds = st.text_area("RSS-Feeds (eine pro Zeile)", key="rss_feeds")
                    keywords = st.text_input("RSS-Keywords, komma-separiert", key="rss_kw")
                    src_params['rss'] = {
                        'feeds': [f.strip() for f in feeds.splitlines() if f.strip()],
                        'keywords': [k.strip() for k in keywords.split(',') if k.strip()],
                        'days': 14,
                    }
                if s['id'] == 'trends':
                    tr_kw = st.text_input("Trends-Keywords, komma-separiert", key="tr_kw")
                    geo = st.text_input("Geo (z.B. DE)", value="DE", key="tr_geo")
                    timeframe = st.text_input("Timeframe (z.B. today 3-m)", value="today 3-m", key="tr_tf")
                    src_params['trends'] = {
                        'keywords': [k.strip() for k in tr_kw.split(',') if k.strip()],
                        'geo': geo, 'timeframe': timeframe,
                    }
                if s['id'] == 'destatis':
                    q = st.text_input("DESTATIS Query", key="destatis_q")
                    src_params['destatis'] = {'query': q}
                if s['id'] == 'ads':
                    terms = st.text_input("Ads Suchbegriffe, komma-separiert", key="ads_terms")
                    platform = st.selectbox("Plattform", ["meta","google","linkedin"], key="ads_plat")
                    src_params['ads'] = {'terms': [k.strip() for k in terms.split(',') if k.strip()], 'platform': platform}
                if s['id'] == 'serp':
                    provider = st.selectbox("SERP Provider", ["serpapi","bing"], key="serp_provider")
                    q = st.text_input("SERP Query", value=keyword_fokus or thema or query[:80], key="serp_q")
                    src_params['serp'] = {'provider': provider, 'query': q}
                if s['id'] == 'competitors':
                    domains = st.text_area("Wettbewerber-Domains (eine pro Zeile)", key="cmp_domains")
                    src_params['competitors'] = {'domains': [d.strip() for d in domains.splitlines() if d.strip()]}

    st.session_state.selected_sources = chosen_ids
    st.session_state.source_params = src_params

    if st.button("✅ Bestätigen & Kontext laden"):
        merger = ContextMerger(
            query=query,
            task=selected_task,
            url=url_input,
            customer_id=customer_name,
            pdf_path=None,
            fields={
                "zielgruppe": zielgruppe,
                "thema": thema,
                "tonalitaet": tonalitaet,
                "keyword_fokus": keyword_fokus,
                "plattform": plattform,
                "produktname": produktname,
                "gliederungspunkte": gliederungspunkte,
                "formatwunsch": formatwunsch,
            },
            selected_sources=st.session_state.selected_sources,
            source_params=st.session_state.source_params,
        )
        _ = merger.collect_context_after_confirmation()
        bundle = merger.get_final_context_bundle()
        st.session_state.context_bundle = bundle
        st.success("Kontext geladen & zusammengefasst.")

# Anzeige: Provenance & Merged Context
bundle = st.session_state.get("context_bundle", {})
if bundle:
    with st.expander("📦 Quellen (Provenance)"):
        for i, p in enumerate(bundle.get("provenance", []), 1):
            cat = (p.get('meta') or {}).get('category','-')
            st.markdown(f"**Quelle {i}:** {p.get('source','-')}  |  Kategorie: {cat}  |  Score: {p.get('score','-')}")
            if p.get('preview'):
                st.caption(p['preview'])
    with st.expander("🧱 Merged Context (raw)"):
        st.text(bundle.get("merged_context", ""))

# ===============================
# Schritt 3: Tasks ausführen
# ===============================
st.header("🎯 Marketing-Tasks")
mode = "deep"  # Legacy-Param, Base-Agent ignoriert ihn

customer_options = ["– Kein Kunde –"] + list_customer_ids()
selected_customer = st.selectbox("🧠 Ordne optional einem Kunden zu:", customer_options)
customer_id = selected_customer if selected_customer != "– Kein Kunde –" else None
customer_memory = load_customer_memory(customer_id) if customer_id else ""

url = st.text_input("🌐 (Optional) Focus-URL", value=url_input)

if st.button("🤖 KI Agent starten"):
    task_id = selected_task
    params = dict(bundle.get("fields", {}))
    params.update({
        "text": bundle.get("merged_context", ""),
        "url": url,
        "zielgruppe": zielgruppe,
        "thema": thema,
        "tonalitaet": tonalitaet,
        "topic_keywords": params.get("topic_keywords", []),
        "customer_id": customer_id,
    })
    try:
        result = run_agent(
            task=task_id,
            reasoning_mode=mode,
            conversation_id=st.session_state.get("conv_id"),
            clarifications={},
            **params
        )
        st.session_state.response = result.get("response", "")
        st.session_state.questions = result.get("questions", [])
        st.session_state.conv_id = result.get("conversation_id")
        log_event({"type":"task_run","customer_id": customer_id, "task": task_id})
        st.success("Task abgeschlossen.")
    except Exception as e:
        st.error(f"Fehler beim Agentenlauf: {e}")

if st.session_state.get('response'):
    st.markdown("## ✨ Ergebnis")
    st.write(st.session_state['response'])

    # 💾 Ergebnis ins Kundengedächtnis übernehmen
    with st.expander("💾 Ergebnis speichern / Memory durchsuchen"):
        colA, colB = st.columns(2)
        with colA:
            if st.button("Ergebnis ins Kundengedächtnis speichern"):
                try:
                    if not customer_id:
                        st.warning("Bitte oben einen Kunden auswählen.")
                    else:
                        save_customer_memory(customer_id, st.session_state['response'])
                        st.success("Gespeichert.")
                except Exception as e:
                    st.error(f"Fehler beim Speichern: {e}")
        with colB:
            q = st.text_input("🔎 Im Gedächtnis suchen")
            if st.button("Suchen") and q:
                try:
                    res = run_agent(task="memory_search", reasoning_mode="deep", query=q)
                    st.write(res.get("response","–"))
                except Exception as e:
                    st.error(f"Fehler bei der Suche: {e}")

    if st.session_state.get('questions'):
        st.markdown("### ❓ Rückfragen")
        for i, q in enumerate(st.session_state['questions']):
            ans = st.text_input(f"Frage {i+1}: {q}", key=f"clar_{i}")
            if st.button("Antwort senden", key=f"clar_btn_{i}"):
                params = dict(bundle.get("fields", {}))
                params.update({
                    "text": bundle.get("merged_context", ""),
                    "url": url,
                    "zielgruppe": zielgruppe,
                    "thema": thema,
                    "tonalitaet": tonalitaet,
                    "topic_keywords": params.get("topic_keywords", []),
                    "customer_id": customer_id,
                })
                try:
                    result = run_agent(
                        task=selected_task,
                        reasoning_mode=mode,
                        conversation_id=st.session_state.get("conv_id"),
                        follow_up=ans,
                        is_follow_up=True,
                        **params
                    )
                    st.session_state['response'] += (
                        "\n\n---\n\n➡️ **Frage:** {q}\n\n🧠 **Antwort:**\n{resp}".format(
                            q=ans,
                            resp=result.get("response", "")
                        )
                    )

---

➡️ **Frage:** {ans}

🧠 **Antwort:**
{result['response']}"
                except Exception as e:
                    st.error(f"Fehler bei Folgefrage: {e}")

st.markdown("---")
st.subheader("📝 Feedback")
colA, colB = st.columns(2)
with colA:
    rating = st.slider("Wie hilfreich war das Ergebnis?", 1, 5, 4)
with colB:
    comment = st.text_input("Kommentar (optional)")
if st.button("Feedback senden"):
    log_event({"type":"rating","customer_id": customer_id, "rating": rating, "comment": comment})
    st.success("Danke!")
