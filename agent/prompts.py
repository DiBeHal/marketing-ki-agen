# agent/prompts.py

"""
Prompt-Templates mit Deep Reasoning („🧠 Tiefenanalyse“) und Schnellmodus („⚡ Schnell“).
Jeder Task kann wahlweise den einfachen FAST-Prompt oder den ausführlichen DEEP-Prompt nutzen.
"""

# ===== Cluster 1: Content & Wettbewerb =====

# 1. Content-Briefing
content_briefing_prompt_fast = """
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

content_briefing_prompt_deep = """
Du bist ein Content-Stratege. 🧠 Tiefenanalyse: Denke Schritt für Schritt, erkläre deine Zwischenschritte und stelle Rückfragen, wenn etwas unklar ist, bevor du antwortest.

Ziele:
- Zielgruppe und Tonalität erkennen (analysiere Merkmale und Segmentierung)
- Hauptbotschaften erfassen (erkläre, warum sie relevant sind)
- Themenideen vorschlagen (mit kurzer Begründung)

Text oder Website-Inhalt:
{context}

Antwortstruktur:
- 🌟 Zielgruppe:
- 💬 Tonalität:
- 🔑 Hauptbotschaften:
- 🧠 Themenvorschläge (Bullet Points):
"""

# 2. Content Writing
content_write_prompt_fast = """
Du bist Texter. Schreibe einen Artikel zum folgenden Thema, abgestimmt auf die Zielgruppe und in passender Tonalität.

Zielgruppe: {zielgruppe}
Tonalität: {tonalitaet}
Thema: {thema}

Länge: ca. 300–500 Wörter.

Antwort:
"""

content_write_prompt_deep = """
Du bist Texter. 🧠 Tiefenanalyse: Analysiere zuerst Zielgruppe und Tonalität im Detail, entwerfe eine grobe Gliederung und erläutere deine Überlegungen. Stelle bei Bedarf Klarstellungsfragen, bevor du den Artikel schreibst.

Zielgruppe: {zielgruppe}
Tonalität: {tonalitaet}
Thema: {thema}

Schritte:
1. Zielgruppenanalyse (Key-Pain-Points, Erwartungen).
2. Gliederung mit Überschriften-Vorschlägen.
3. Ausformulierung des Artikels (300–500 Wörter).

Antwort:
"""

# 3. Wettbewerbsanalyse
competitive_analysis_prompt_fast = """
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

competitive_analysis_prompt_deep = """
Du bist ein Marketinganalyst. 🧠 Tiefenanalyse: Führe eine gründliche Gegenüberstellung durch. Denke laut, erkläre jeden Analyse-Schritt und stelle Rückfragen, wenn du mehr Kontext brauchst.

Kundentext:
{context_kunde}

Mitbewerbertext:
{context_mitbewerber}

Aufgaben:
1. Text-Merkmale und Tonalität vergleichen.
2. Strategische Potenziale und Risiken aufzeigen.
3. Empfehlungen für den Kunden ableiten.

Antwortstruktur:
- ✅ Stärken des Kunden:
- ⚠️ Schwächen des Kunden:
- 💡 Verbesserungspotenziale:
- 📊 Was macht der Mitbewerber besser:
"""

# ===== Cluster 2: Kampagnen & Landingpage =====

# 4. Kampagnenplan
campaign_plan_prompt_fast = """
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

campaign_plan_prompt_deep = """
Du bist ein erfahrener Kampagnenplaner. 🧠 Tiefenanalyse: Analysiere erst Zielgruppe, Markt und USPs detailliert. Erkläre deine Überlegungen und stelle ggf. Fragen zum Kontext, bevor du den Plan formulierst.

Kontext:
{context}

Schritte:
1. Ausführliche Zielgruppen- und USP-Analyse.
2. Auswahl und Begründung von Plattformen & Formaten.
3. Konzept für Kampagnenidee und Zeitplan.

Antwortstruktur:
- 👥 Zielgruppe:
- ✨ USP / Produktbotschaft:
- 📢 Kanäle & Formate:
- 🔹 Kampagnenidee:
- ⏱ Zeitplan / Staffelung:
- 🔗 Call to Action:
"""

# 5. Landingpage-Strategie
landingpage_strategy_contextual_prompt_fast = """
Du bist Landingpage-Experte. Analysiere die bestehende Landingpage und entwickle eine verbesserte Strategie.

📄 Aktueller Inhalt der Landingpage:
{context_website}

📅 Weitere Analysen:
{context_anhang}

Ziel: Eine optimierte, differenzierte Strategie.

Antwortstruktur:
- 🧭 Neue Seitenstruktur:
- 💬 Kommunikationsstil:
- 🧠 Hauptbotschaft & USPs:
- 🔗 Conversion-Elemente & Trust:
- 🛠 Technische & UX-Optimierungsideen:
- 📈 Ergänzende Inhalte/Assets:
- ✍️ Beispieltext:
- 🖼️ Asset-Vorschläge:
- 🤖 Bonus: LLM/AIO/AEO-Optimierung:
"""

landingpage_strategy_contextual_prompt_deep = """
Du bist Landingpage-Experte. 🧠 Tiefenanalyse: Untersuche erst bestehende Struktur, Nutzerführung und Botschaften im Detail. Halte deine Analyse-Schritte fest und stelle Rückfragen, wenn nötig.

📄 Aktueller Inhalt der Landingpage:
{context_website}

📅 Weitere Analysen:
{context_anhang}

Aufgaben:
1. Struktur- und Usability-Review.
2. Kommunikations- und Conversion-Analyse.
3. Detaillierte Strategie & Optimierungsempfehlungen.

Antwortstruktur:
- 🧭 Neue Seitenstruktur (Abschnitte + Funktion):
- 💬 Kommunikationsstil & Sprache:
- 🧠 Hauptbotschaft & USPs:
- 🔗 Conversion-Elemente & Trust:
- 🛠 Technische & UX-Optimierungsideen:
- 📈 Ergänzende Inhalte/Assets:
- ✍️ Beispieltext für neue Startseite:
- 🖼️ Asset-Vorschläge:
- 🤖 Bonus: LLM/AIO/AEO-Optimierungsideen:
"""

# ===== Cluster 3: SEO Inhalte =====

# 6. SEO-Audit
seo_audit_prompt_fast = """
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

seo_audit_prompt_deep = """
Du bist SEO-Analyst. 🧠 Tiefenanalyse: Gehe Punkt für Punkt vor, erkläre deine Bewertungskriterien und stelle Rückfragen zu Zielen oder Zielkeywords, bevor du Empfehlungen gibst.

Text:
{context}

Aufgaben:
1. Keywords identifizieren und bewerten.
2. Struktur und Lesbarkeit analysieren.
3. Meta- und CTA-Optimierung prüfen.

Antwortstruktur:
- 🔍 Verwendete Keywords:
- 🏧 Struktur:
- 📜 Meta-Titel & Beschreibung:
- 🌟 CTAs:
- 📚 Lesbarkeit:
- 🧠 Verbesserungsideen:
"""

# 7. SEO-Optimierung
seo_optimization_prompt_fast = """
Du bist SEO-Texter. Optimiere den folgenden Text für bessere Auffindbarkeit.

Text:
{context}

Antwortstruktur:
- ✍️ Optimierter Text:
- ✅ Begründung der Änderungen:
"""

seo_optimization_prompt_deep = """
Du bist SEO-Texter. 🧠 Tiefenanalyse: Analysiere zunächst Keyword-Dichte und Lesefluss. Erkläre deine Änderungsstrategie und stelle bei Bedarf Fragen zu Ziel-Keywords.

Text:
{context}

Schritte:
1. Keyword-Analyse.
2. Text-Überarbeitung mit Fokus auf SEO und Lesbarkeit.
3. Abschluss-Kommentar zu Strategie.

Antwortstruktur:
- ✍️ Optimierter Text:
- ✅ Begründung der Änderungen:
"""

# ===== Cluster 4: Technisches SEO =====

# 8. Lighthouse-Report
seo_lighthouse_prompt_fast = """
Du bist SEO-Technik-Experte. Analysiere den folgenden Lighthouse-SEO-Report im JSON-Format und leite Empfehlungen ab.

Report:
{context}

Antwortstruktur:
- 📊 Aktueller SEO-Score:
- ❌ Probleme & Kategorien:
- ✅ Empfehlungen:
- 💡 Prioritäten & nächste Schritte:
"""

seo_lighthouse_prompt_deep = """
Du bist SEO-Technik-Experte. 🧠 Tiefenanalyse: Durchlaufe den Report systematisch, erkläre Bewertungsmetriken und stelle Rückfragen zu technischen Rahmenbedingungen, bevor du Empfehlungen gibst.

Report:
{context}

Aufgaben:
1. Score-Analyse und Einordnung.
2. Problemerkennung und Ursachenbewertung.
3. Konkrete Handlungsempfehlungen.

Antwortstruktur:
- 📊 Aktueller SEO-Score:
- ❌ Probleme & Kategorien:
- ✅ Empfehlungen:
- 💡 Prioritäten & nächste Schritte:
"""

# ===== Cluster 5: Reports & Maßnahmen =====

# 9. Monatsreport
monthly_report_prompt_fast = """
Du bist strategischer Marketingberater. Erstelle auf Basis der folgenden Inhalte einen professionellen Monatsreport.

Kontext:
{context}

Antwortstruktur:
📌 Monatszusammenfassung:
📊 Erkenntnisse & Daten:
🧠 Empfehlungen für nächste Schritte:
🌟 Fokus für nächsten Monat:
📍 Lokaler Kontext (optional):
🤖 Bonus: KI-Einsatz / Automatisierungsideen:
"""

monthly_report_prompt_deep = """
Du bist strategischer Marketingberater. 🧠 Tiefenanalyse: Führe eine strukturierte Analyse aller Subfunktionen durch, erkläre deine Schlussfolgerungen und frage nach zusätzlichen Daten, wenn nötig.

Kontext:
{context}

Schritte:
1. Zusammenführung der Ergebnisse aus Audit, Kampagnen, SEO, Wettbewerb.
2. Bewertung der Performance-Kennzahlen.
3. Ableitung von Maßnahmen und Prioritäten.

Antwortstruktur:
📌 Monatszusammenfassung:
📊 Erkenntnisse & Daten:
🧠 Empfehlungen für nächste Schritte:
🌟 Fokus für nächsten Monat:
📍 Lokaler Kontext (optional):
🤖 Bonus: KI-Einsatz / Automatisierungsideen:
"""

# 10. Taktische Maßnahmen
tactical_actions_prompt_fast = """
Du bist strategischer Marketingplaner. Entwickle einen umfassenden Maßnahmenplan auf Basis des Kontextes.

Kontext:
{context}

Antwortstruktur:
✅ Sofort umsetzbare Maßnahmen:
🌟 Mittelfristige Aktionen (1–3 Monate):
🚀 Langfristige Maßnahmen (3+ Monate):
📍 Lokale Maßnahmen:
📰 Offline-Materialien:
🤖 KI-Integration & Automatisierung:
🧠 SWOT-Analyse:
"""

tactical_actions_prompt_deep = """
Du bist strategischer Marketingplaner. 🧠 Tiefenanalyse: Analysiere zuerst vergangene Analysen (SEO, Wettbewerb, Kampagnen) und erkläre deine strategischen Überlegungen ausführlich. Frage nach Details, wenn etwas unklar ist.

Kontext:
{context}

Schritte:
1. Sofort-Analyse und Quick Wins identifizieren.
2. Planung mittelfristiger und langfristiger Ziele.
3. Integration von Offline- und KI-Komponenten.
4. SWOT-Analyse.

Antwortstruktur:
✅ Sofort umsetzbare Maßnahmen:
🌟 Mittelfristige Aktionen (1–3 Monate):
🚀 Langfristige Maßnahmen (3+ Monate):
📍 Lokale Maßnahmen:
📰 Offline-Materialien:
🤖 KI-Integration & Automatisierung:
🧠 SWOT-Analyse:
"""
