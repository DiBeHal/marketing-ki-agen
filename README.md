# 🧠 Marketing KI-Agent

Ein vielseitiger, modularer KI-Agent zur Unterstützung von Marketingstrategien für kleine Unternehmen. Fokus auf Automatisierung, Tiefe und Benutzerfreundlichkeit in den Bereichen SEO, Content, Wettbewerbsanalyse, Kampagnenplanung und Reporting.

---

## 🚀 Features

- 🔍 SEO-Audits & Optimierungen (inkl. Lighthouse und PDF-Upload)
- 🧠 Content-Briefings & Writing (auch mit automatischen Themenvorschlägen)
- 📡 Themenbasierte Anbindung an RSS, Google Trends, DESTATIS/Eurostat (Deep-Modus)
- 🆚 Wettbewerbsanalyse mit Webseitenvergleich & Ads-Bibliotheken (Google, Meta, LinkedIn)
- 📈 Monatsreporting & Maßnahmenpläne
- 🎯 Kampagnenplanung mit Kontextdaten
- 💾 Kundengedächtnis zur Speicherung individueller Analysen
- 💬 Rückfragen-Handling & Follow-up-Funktion

---

## ⚙️ Setup & Start (lokal)

```bash
git clone <REPO>
cd <REPO>
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

---

## 🧩 Module & Architektur

- `streamlit_app.py`: Haupt-UI mit dynamischem Agentenaufruf, Rückfragen-Loop & automatischer Datenanreicherung
- `base_agent.py`: Kernlogik für Prompt-Auswahl, Kontextaggregation & Quellensteuerung
- `agent/tools/ads_scraper.py`: Extrahiert Werbeanzeigen aus LinkedIn, Meta & Google
- `agent/services/rss.py`, `trends.py`, `destatis.py`: Datenabruf externer Quellen basierend auf automatisch extrahierten Themen
- `prompts.py`: Modulare, taskbasierte Prompt-Vorlagen (fast/deep)

---

## 🧠 Intelligente Datenintegration

**Deep-Modus** nutzt automatisch:
- RSS-Snippets
- Google Trends
- DESTATIS/Eurostat-Daten

Optional werden Themen aus Zielgruppe, Text & Thema extrahiert und vorab zur Bestätigung angezeigt (abschaltbar über Checkbox).

Diese Daten fließen intelligent in folgende Tasks ein:
- Content Analyse
- Content Writing (auch im Fast-Modus)
- Kampagnenplanung
- Landingpage Strategie
- SEO Optimierung
- Monatsreport
- Marketingmaßnahmen planen
- Wettbewerbsanalyse (mit DESTATIS)

---

## 💬 Rückfragen & Follow-ups

- Agent kann während der Analyse Rückfragen stellen (nur Deep-Modus)
- Nutzer kann auch nach der Antwort gezielt Rückfragen stellen
- Folgeantworten bauen auf vorheriger Konversation auf

---

## 🗃 Dateistruktur (Auszug)

```
├── streamlit_app.py
├── agent/
│   ├── base_agent.py
│   ├── tools/
│   │   └── ads_scraper.py
│   ├── services/
│   │   ├── rss.py
│   │   ├── trends.py
│   │   └── destatis.py
│   ├── prompts.py
│   └── ...
├── requirements.txt
├── .env
└── README.md
```

---

## 📌 Hinweise

- PDF-Uploads werden intelligent integriert, wo sinnvoll
- Der Deep-Modus ist deutlich kontextreicher & datengetriebener
- Fehlerbehandlung & Logging für Datenquellen und Ads wurden verbessert

---

## 🧪 Geplant/Nächste Schritte

- LangChain Memory/DB-Speicher statt Session
- UI-Optimierung & mehr Kontrollmöglichkeiten (Checkboxes, Debug-Ansicht)
- Exportfunktion für Reports & Analysen

---

📣 Bei Fragen oder Ideen → Issues öffnen oder Feedback im UI abgeben!
