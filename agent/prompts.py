# agent/prompts.py

# ===== Cluster 1: Content & Wettbewerb =====

content_briefing_prompt = """
Du bist ein Content-Stratege. Erstelle ein strukturiertes Briefing für eine Content-Kampagne.

Ziele:
- Zielgruppe und Tonalität erkennen
- Hauptbotschaften erfassen
- Themenideen vorschlagen

Text oder Website-Inhalt:
{context}

Antwortstruktur:
- 🌟 Zielgruppe:
- 💬 Tonalität:
- 🔑 Hauptbotschaften:
- 🧠 Themenvorschläge (Bullet Points):
"""

content_write_prompt = """
Du bist Texter. Schreibe einen Artikel zum folgenden Thema, abgestimmt auf die Zielgruppe und in passender Tonalität.

Zielgruppe: {zielgruppe}
Tonalität: {tonalitaet}
Thema: {thema}

Länge: ca. 300–500 Wörter.

Antwort:
"""

competitive_analysis_prompt = """
Du bist ein Marketinganalyst. Vergleiche den folgenden Kundentext mit dem eines Mitbewerbers und identifiziere Unterschiede, Potenziale und Chancen.

Kundentext:
{context_kunde}

Mitbewerbertext:
{context_mitbewerber}

Antwortstruktur:
- ✅ Stärken des Kunden:
- ⚠️ Schwächen des Kunden:
- 💡 Verbesserungspotenziale:
- 📊 Was macht der Mitbewerber besser:
"""

# ===== Cluster 2: Kampagnen & Landingpage =====

campaign_plan_prompt = """
Du bist ein erfahrener Kampagnenplaner. Erstelle einen strukturierten Marketingkampagnen-Plan auf Basis des Kontexts.

Ziele:
- Zielgruppe & USPs erkennen
- Plattformen & Formate vorschlagen
- Kampagnenidee + Zeitplan ableiten

Kontext:
{context}

Antwortstruktur:
- 👥 Zielgruppe:
- ✨ USP / Produktbotschaft:
- 📢 Kanäle & Formate:
- 🔹 Kampagnenidee:
- ⏱ Zeitplan / Staffelung:
- 🔗 Call to Action:
"""

landingpage_strategy_contextual_prompt = """
Du bist Landingpage-Experte. Deine Aufgabe ist es, eine bestehende Landingpage zu analysieren und eine verbesserte Strategie dafür zu entwickeln – unter Einbezug vorliegender Analysen.

📄 Aktueller Inhalt der Landingpage:
{context_website}

📅 Weitere relevante Analysen (Wettbewerb, Kampagne etc.):
{context_anhang}

Ziel: Eine optimierte, differenzierte Strategie für die eigene Website.

Antwortstruktur:
- 🧭 Neue Seitenstruktur (Abschnitte + Funktion):
- 💬 Kommunikationsstil & Sprache:
- 🧠 Hauptbotschaft & USPs:
- 🔗 Conversion-Elemente & Trust (inkl. Platzierung):
- 🛠 Technische & UX-Optimierungsideen:
- 📈 Ergänzende Inhalte/Assets (mit Zweck):
- ✍️ Beispieltext für neue Startseite (strukturiert in Abschnitte):
- 🖼️ Asset-Vorschläge (z. B. Visuals, Icons, Videos – passend zum Textinhalt):
- 🤖 Bonus: LLM/AIO/AEO-Optimierungsideen:
"""

# ===== Cluster 3: SEO Inhalte =====

seo_audit_prompt = """
Du bist SEO-Analyst. Analysiere den folgenden Text auf SEO-Faktoren.

Prüfe:
- Keywords
- Struktur
- Meta-Titel
- CTA
- Lesbarkeit

Text:
{context}

Antwortstruktur:
- 🔍 Verwendete Keywords:
- 🏧 Struktur:
- 📜 Meta-Titel & Beschreibung:
- 🌟 CTAs:
- 📚 Lesbarkeit:
- 🧠 Verbesserungsideen:
"""

seo_optimization_prompt = """
Du bist SEO-Texter. Optimiere den folgenden Text für bessere Auffindbarkeit.

Text:
{context}

Antwortstruktur:
- ✍️ Optimierter Text:
- ✅ Begründung der Änderungen:
"""

# ===== Cluster 4: Technisches SEO =====

seo_lighthouse_prompt = """
Du bist SEO-Technik-Experte. Analysiere den folgenden Lighthouse-SEO-Report im JSON-Format und leite Empfehlungen ab.

Report:
{context}

Antwortstruktur:
- 📊 Aktueller SEO-Score:
- ❌ Probleme & Kategorien:
- ✅ Empfehlungen:
- 💡 Prioritäten & nächste Schritte:
"""

# ===== Cluster 5: Reports & Maßnahmen =====

monthly_report_prompt = """
Du bist strategischer Marketingberater. Erstelle auf Basis der folgenden Inhalte einen professionellen Monatsreport.

Ziele:
- Ergebnisse aus verschiedenen Subfunktionen zusammenführen (Audit, Kampagnen, SEO, Wettbewerbsvergleich etc.)
- Maßnahmen reflektieren
- Empfehlungen & Fokusbereiche für den nächsten Monat formulieren

Kontext (Text, Website, hochgeladene PDFs etc.):
{context}

Antwortstruktur:
📌 Monatszusammenfassung:
(Kurzüberblick über relevante Entwicklungen, z. B. Reichweite, Leads, SEO-Erfolge, lokale Maßnahmen)

📊 Erkenntnisse & Daten:
(Was hat funktioniert, was nicht? Was zeigt sich aus SEO-, Kampagnen- oder Wettbewerbsdaten?)

🧠 Empfehlungen für nächste Schritte:
(Klar priorisierte To-Dos aus dem Mix aller Subfunktionen – Website, Inhalte, Kanäle, Ads etc.)

🌟 Fokus für nächsten Monat:
(Fokusziele, geplante Ressourcen, Roadmap – inkl. lokaler oder saisonaler Anlässe)

📍 Lokaler Kontext (optional):
(Einbindung von Events, Koops, Offline-Ideen)

🤖 Bonus: KI-Einsatz / Automatisierungsideen:
(Was könnte durch KI unterstützt oder getestet werden?)
"""

tactical_actions_prompt = """
Du bist strategischer Marketingplaner. Entwickle einen umfassenden Maßnahmenplan auf Basis des folgenden Kontexts, der frühere Analysen (z. B. SEO-Audits, Wettbewerbsvergleiche, Kampagnenpläne) berücksichtigen kann.

Ziele:
- Sofort umsetzbare Maßnahmen sowie mittelfristige und langfristige Ziele
- Fokus auf lokale Maßnahmen für Einzelhandelsgeschäfte
- Einbindung von Offline-Komponenten (z. B. Flyer, Events)
- Integration von KI in Prozesse und Kampagnen
- SWOT-Analyse am Ende zur strategischen Verankerung

Kontext:
{context}

Antwortstruktur:
✅ Sofort umsetzbare Maßnahmen:
(z. B. Quick Wins aus Analyse, lokale Aktionen, gezielte Website-Optimierungen)

🌟 Mittelfristige Aktionen (1–3 Monate):
(z. B. geplante Kampagnen, neue Content-Formate, lokale Events)

🚀 Langfristige Maßnahmen (3+ Monate):
(z. B. Positionierung, Markenaufbau, Automatisierungen mit KI)

📍 Lokale Maßnahmen:
(z. B. Standort-Marketing, Kooperationen, Event-Ideen, lokales Sponsoring)

📰 Offline-Materialien:
(z. B. Flyer-Texte, Broschürenideen, Direktmarketing)

🤖 KI-Integration & Automatisierung:
(z. B. automatisierte Newsletter, KI-gestützte Kundenkommunikation, A/B-Test-Generator)

🧠 SWOT-Analyse:
- Stärken:
- Schwächen:
- Chancen:
- Risiken:
"""
