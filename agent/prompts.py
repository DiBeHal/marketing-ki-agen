# agent/prompts.py

"""
Prompt-Templates mit Deep Reasoning ("🧠 Tiefenanalyse") und Schnellmodus ("⚡ Schnell").
Jeder Task kann wahlweise den einfachen FAST-Prompt oder den ausführlichen DEEP-Prompt nutzen.
"""

# ===== Cluster 1: Content =====

# 1. Content-Analyse (früher Content-Briefing)
content_analysis_prompt_fast = """
Du bist ein erfahrener Content-Stratege. Analysiere den folgenden Input effizient und praxisorientiert.

Ziel:
- Zielgruppen-Merkmale & Ansprache ableiten
- Tonalität & Markenstil einschätzen
- Kernbotschaften herausarbeiten
- Erste Content-Ideen formulieren
- Relevante Trends & Marktdaten berücksichtigen

Eingabe (Text, Website-Auszug oder Kombination):
{context}

Zusätzliche Informationen:
- 🔎 Branchentrends (RSS): {rss_snippets}
- 📈 Google Trends: {trends_insights}
- 🧮 Marktdaten (DESTATIS/Eurostat): {destatis_stats}

Antwortstruktur:
- 👥 Zielgruppen-Segmente (Alter, Rolle, Bedarf):
- 🎙️ Tonalität & Kommunikationsstil:
- 🧩 Hauptbotschaften (max. 3 Bullet Points):
- 💡 Erste Content-Ideen (je 1 Satz):
- 📰 Relevante Trends & News:
- 📊 Markt-Kennzahlen (falls vorhanden):
"""

content_analysis_prompt_deep = """
Du bist ein erfahrener Content-Stratege. Führe eine gründliche Content-Analyse durch und dokumentiere deine Gedanken strukturiert.

Ziel:
- Zielgruppe, Tonalität und Botschaften systematisch erfassen
- Content-Struktur & SEO bewerten
- Potenziale & Formate für neue Inhalte ableiten
- Trends & Marktdaten sinnvoll einbinden

Eingabe (Text/Website-Kontext):
{context}

Externe Informationen:
- 📰 Branchentrends (RSS): {rss_snippets}
- 📈 Google Trends: {trends_insights}
- 📊 Marktdaten (DESTATIS/Eurostat): {destatis_stats}

Antwortstruktur:
- 👥 Zielgruppen-Segmente (inklsuive Pain-Points, Bedürfnisse, bevorzugte Kanäle; mit kurzen Begründungen):
- 🎙️ Tonalität & Markenstil (inkl. Stilbeispiel):
- 🧩 Hauptbotschaften (Top 3, je mit Nutzen-Begründung):
- 🔍 SEO-Hinweise (Meta, Keywords, Snippet-Chancen, Interne Verlinkungstipps):
- 🧠 Neue Content-Ideen (Thema + Format + Nutzen):
- 🧱 Struktur- und Format-Tipps (H1-H3, Absätze, CTAs):
- 📚 Lesbarkeitskommentar (kurz & praxisnah):
- 📰 Relevante Trends & News (mit Bezug zur Marke):
- Vergleich mit Top-3 Google SERP (Welche Aspekte fehlen im Vergleich?):
- 📊 Marktdaten & Chancen:
- 📣 CTA - Wie kann man besser zum Ziel überleiten (inklusive konkreter Call-to-Action-Empfehlungen):
- ✅ Optimierungsvorschläge (Bullet Points, priorisiert):
"""

# ===== Cluster 2: Content Writing =====
content_write_prompt_fast = """
Du bist ein erfahrener Texter. Verfasse einen kompakten Artikel (ca. 300-500 Wörter) zu folgendem Thema - abgestimmt auf Zielgruppe und Tonalität.

Zielgruppe: {zielgruppe}  
Tonalität: {tonalitaet}  
Thema: {thema}

Zusätzliche Infos (optional):
- 📰 Branchentrends: {rss_snippets}
- 📈 Google Trends: {trends_insights}
- 📊 Marktdaten: {destatis_stats}

Vorgehen:
- Starte mit einem einprägsamen Einstieg (Hook)
- Leite direkt zum Nutzen des Produkts/Dienstleistung über
- Schreibe aktiv, klar, überzeugend

Abschnitt:  
✍️ Artikeltext:
"""

content_write_prompt_deep = """
Du bist ein erfahrener Texter. Führe zunächst eine inhaltliche Analyse durch und schreibe anschließend einen klar strukturierten Artikel (300-500 Wörter).

Zielgruppe: {zielgruppe}  
Tonalität: {tonalitaet}  
Thema: {thema}

Externe Informationen (optional):
- 📰 Branchentrends: {rss_snippets}
- 📈 Google Trends: {trends_insights}
- 📊 Marktdaten: {destatis_stats}

Vorgehen:
1. Zielgruppenanalyse (Bedürfnisse, Erwartungen, Kommunikationsstil)
2. Grobe Gliederung (Überschriften, Artikelstruktur)
3. Hook & Nutzenformulierung (emotional oder datenbasiert)
4. Artikeltext (300-500 Wörter, aktiv, klar)
5. SEO-Elemente:
   - Top-3 Keywords (natürlich integriert)
   - Meta-Title (max. 60 Zeichen)
   - Meta-Description (max. 155 Zeichen)
6. Abschluss mit Call-to-Action

Antwortstruktur:
- 👥 Zielgruppenprofil:
- 🗂️ Gliederungsvorschlag (inkl. Überschriften):
- ✍️ Artikeltext:
- 🔍 SEO-Elemente:
- 📌 Hook & Produkt-Überleitung:
- 📣 Call-to-Action:
"""

# ===== Cluster 3: Wettbewerbsanalyse =====

competitive_analysis_prompt_fast = """
Du bist ein Marketinganalyst. Vergleiche die Online-Identität (Inhalte, Tonalität und Formate) des Kunden mit der eines oder mehrerer Mitbewerber.
Beziehe folgende Aspekte mit ein:

1. **Website-Analyse**
   - Informationsarchitektur (Menü, Navigation, Seitenstruktur)
   - Zielgruppenansprache & USPs auf der Website
   - Visuelles Design & Branding-Elemente
   - Call-to-Action-Platzierungen

2. **Externe Präsenz**
   - Artikel, Pressemitteilungen, Branchenverzeichnisse (z. B. XING, Crunchbase)
   - Social-Media-Aktivität (LinkedIn, Twitter, Instagram)

Optional (Frontend-Auswahl):
- Öffentlich verfügbare Ads (Google Ads Transparency, Facebook Ad Library, LinkedIn Ads).
  Verwende Platzhalter:
  {google_ads}
  {facebook_ads}
  {linkedin_ads}

3. Suche nach zusätzlichen relevanten Mitbewerbern basierend auf Branchen-Keywords und Netzwerk-Vorschlägen.

Antwortstruktur:
- Stärken und Schwächen des Kunden (Website & Branding):
- Inhaltliche Schwerpunkte:
- Tonalität und Stil:
- Externe Präsenz & Erwähnungen:
- Relevante Ads Insights (falls ausgewählt):
- Zusätzliche Mitbewerber (Namen & kurze Begründung):
- Chancen für Abgrenzung:
"""

competitive_analysis_prompt_deep = """
Du bist ein Marketinganalyst. 🧠 Tiefenanalyse: Führe eine umfassende, strukturierte Wettbewerbsanalyse durch. 

Eingabe:
- Eigene Unternehmens-URL oder Text (inkl. Unterseiten):
{contexts_combined_kunde}
- Direkt eingetragene Mitbewerber (inkl. Unterseiten):
{contexts_combined_mitbewerber}

Ergänzende Werbemittel:
- Facebook Ads: {facebook_ads}
- Google Ads: {google_ads}
- LinkedIn Ads: {linkedin_ads}


Aufgaben:
1. **Website-Deep-Dive**
   - Architektonische Übersicht (Menü, Seitenstruktur, Depth)
   - Zielgruppenansprache & USPs
   - Visuelle Kommunikation
   - Call-to-Action-Strategie
   - Technische Performance

2. **Externe Reichweite**
   - Artikel, Presse, Verzeichnisse
   - Social-Media
   - OpenCorporates / Wikidata, falls verfügbar

3. **Ads-Komponente**
   - Analyse verfügbarer Ads:
     • Google: {google_ads}
     • Facebook: {facebook_ads}
     • LinkedIn: {linkedin_ads}

4. **Zusätzliche Mitbewerbersuche**
   - Identifiziere weitere Wettbewerber + Begründung

5. **Strategische Empfehlungen**
   - UX, Content, Performance
   - Externe Präsenz
   - Quick Wins vs. langfristige Projekte

Antwortstruktur:
- 🧭 Positionierung (Claim, Zielgruppe, Nutzenversprechen, Themencluster & Content-Strategie):
- ✅ Stärken & USPs (Website & Branding):
- ⚠️ Schwächen & Risiken:
- 💡 Verbesserungspotenziale:
- 📊 Externe Präsenz (Artikel, Verzeichnisse, Social-Media):
- 📰 Ads Insights:
- 🔍 Neu identifizierte Mitbewerber (mit Begründung):
- 📢 Abgrenzungspotenziale & Lücken:
- 🚀 Empfohlene Maßnahmen (Quick Wins & Langfristiges):
"""

# ===== Cluster 4: Kampagnen =====

# 4. Kampagnenplan
campaign_plan_prompt_fast = """
Du bist ein erfahrener Werbestratege. Erstelle einen kompakten Kampagnenplan (Skizze) auf Basis folgender Eckdaten:
(Text/Website-Kontext):
{context}
Zielgruppe: {zielgruppe}  
Tonalität: {tonalitaet}  
Thema: {thema}

Zusätzliche Hinweise:
- 📰 Branchentrends: {rss_snippets}

Ziele:
- Zielgruppe & USPs identifzieren
- Plattformen & Formate vorschlagen
- Kampagnenidee + Zeitplan ableiten
- Text- und Asset-Ideen formulieren

Antwortstruktur:
- Zielgruppenansprache (Wording & Trigger):
- Hauptbotschaft der Kampagne:
- Werbetexte & Kanäle (mit kurzer Begründung):
- Grober Zeitplan (Monatsschritte, Phasen):
- Erfolgskriterien (konkret, messbar):
- Asset-Vorschläge (Grafiken, Video, Infografik):
"""

campaign_plan_prompt_deep = """
Du bist Werbestratege. Entwickle eine umfassende Kampagnenstrategie basierend auf:

Zielgruppe: {zielgruppe}
Tonalität: {tonalitaet}
Thema: {thema}

Berücksichtige:
- Trends: {rss_snippets}
- Insights: {trends_insights}
- Markt-Statistiken: {destatis_stats}

Schritte:
1. Zielgruppen-Segmentierung und -Analyse:
   - Demografische Merkmale (Alter, Branche, Rolle)
   - Pain-Points & Bedürfnisse

2. USP- & Botschaftsentwicklung:
   - Kernbotschaften (emotional/rational)
   - Priorisierung der Aussagen

3. Plattformen, Formate & Budget:
   - Kanäle (Search, Social, Display, E-Mail)
   - Formate (Text, Video, Carousel, Infografik)
   - Budgetempfehlung (prozentual)

4. Kampagnen-Idee & Kreation:
   - Kernthema & Storytelling-Ansatz
   - Textideen für Headlines & Teaser
   - Vorschläge für Assets

5. Zeitplan & Staffelung:
   - Pre-Launch, Launch, Post-Launch
   - Veröffentlichungsfrequenz

6. KPI & Tracking:
   - Wichtige KPIs (CTR, Conversion-Rate, CPC)
   - A/B-Test-Vorschläge

Antwortstruktur:
- 👥 Zielgruppen-Segmente:
- ✨ USP / Produktbotschaft:
- 📢 Kanäle, Formate & Budget:
- 🔹 Kampagnenidee & Story:
- 🖋️ Text- & Teaser-Ideen:
- 🖼️ Asset-Vorschläge:
- ⏱ Zeitplan / Staffelung:
- 📊 KPI-Empfehlungen:
- 🔬 A/B-Test-Plan:
- 📰 Branchentrends & News:
- 📈 Marktkennzahlen:
- 🔗 Call to Action:
"""

# ===== Cluster 5: Landingpage =====

landingpage_strategy_contextual_prompt_fast = """
Du bist Conversion-Spezialist für digitale Marketing-Kampagnen. Entwickle eine schlanke, wirkungsvolle Strategie für den Aufbau einer Landingpage oder wenn gegeben optimiere die vorhandene.

Ziel: Maximale Relevanz, Klarheit und Conversion-Optimierung

Aktueller Inhalt der Landingpage:
{context_website}

- 👥 Zielgruppe: {zielgruppe}
- 🎯 Ziel: {ziel}
- 🧵 Kontext (Kampagne, Produkt, Trigger): {thema}

Strukturierte Antwort (kurz & präzise):

- 🧠 Erste Impression / Headline-Idee:
- Eine Gliederung der Seite
- ✨ Nutzenversprechen (USP, Value Proposition):
- 📄 Empfohlene Sections (H1-H3 Struktur):
- 🔍 Vertrauen & Beweise (z. B. Social Proof, Zertifikate):
- 🎯 Call-to-Action (Text & Platzierung):
- 🎨 Stil-Tipps (Farben, Bilder, Icons):
- 🖼️ Asset-Vorschläge (Grafiken, Videos, Infografiken):
- 📱 Mobile-Optimierungshinweise:
- 🧭 UX-Tipp zur Scrollführung oder Friction-Punkten:
"""


landingpage_strategy_contextual_prompt_deep = """
Du bist Conversion-Experte mit Fokus auf High-Performance-Landingpages. Entwickle eine fundierte Strategie für die Aufsetzung oder die Optmimierung einer Landing Page auf Basis folgender Angaben:

Landingpage-URL oder Inhalt:
{context_website}

- 👥 Zielgruppe: {zielgruppe}
- 🎯 Ziel: {ziel}
- 🧵 Kontext (Produkt, Dienstleistung, Kampagnenziel): {thema}

Ergänzende Informationen:
- 📰 Branchentrends: {rss_snippets}
- 📈 Suchtrends: {trends_insights}
- 📊 Marktkennzahlen: {destatis_stats}

### Schritte:

1. Zielgruppenanalyse, -ansprache:
   - Bedürfnisse, Hürden, Conversion-Trigger
   - Informationsbedarf vs. Entscheidungsmotivation

2. Kernbotschaft & Emotionale Ansprache:
   - Value Proposition (Nutzenversprechen)
   - Emotionaler vs. rationaler Appeal
   - Headline-Formulierung (inkl. Hook)

3. Strukturvorschlag:
   - Empfohlene Sections inklusiver konkreter Textabschnitte (H1-H3, Abschnitte)
   - Scrolltiefe & visuelle Hierarchie
   - Trust-Elemente (z. B. Social Proof, Siegel, Testimonials)

4. Content & Assets:
   - Copywriting-Tipps für Abschnittstypen
   - Empfehlungen für Bilder, Icons, Grafiken

5. CTA & Interaktionen:
   - Platzierung, Textvorschläge, Conversion-Optimierung
   - Microinteractions & Reduktion von Friction

6. Mobile & UX:
   - Hinweise zur mobilen Optimierung
   - UX-Tipps für responsives Verhalten & Geschwindigkeit

### Antwortstruktur:

- 👤 Zielgruppen-Insights:
- 💬 Headline + Hook-Idee:
- 💎 Nutzenversprechen / USP:
- 📄 Strukturvorschlag (Abschnitte):
- 🔒 Trust-Elemente:
- 🖋️ Text-Tipps (CTA, Abschnitt 1-3):
- 🎨 Asset- und Bildideen:
- 🔗 CTA-Vorschläge & Platzierung:
- 📱 Mobile-Optimierung & UX-Hinweise:
- 🧪 Konversions-Booster oder A/B-Test-Vorschläge:
"""

# ===== Cluster 6: SEO Inhalte =====

seo_audit_prompt_fast = """
Du bist SEO-Experte. Führe ein kompaktes SEO-Audit der folgenden Seite durch:

🔗 URL oder Textinhalt:  
{context}

Schwerpunkte deiner Analyse:
1. Meta-Daten & Snippet-Potenzial:
   - Title, Description (Länge, Keywords, Clickability)
   - Verbesserungsvorschläge

2. Keyword-Relevanz:
   - Fokus-Thema identifizieren
   - Passende semantische Begriffe / Cluster

3. Content-Qualität:
   - Klarheit, Struktur, Keyword-Integration
   - Duplicate/Thin Content vermeiden

4. Nutzerfreundlichkeit:
   - Überschriftenstruktur (H1-H3)
   - Lesbarkeit & Aufbau

5. CTA & Zielerreichungs-Analyse

Antwortstruktur:
- 🔍 Fokus-Thema:
- 🏷️ Meta-Optimierung:
- 🔑 Keyword-Chancen:
- 📄 Content-Feedback:
- 🧭 Struktur- & UX-Hinweise:
- 🧠 Verbesserungsideen:
"""

seo_audit_prompt_deep = """
Du bist ein erfahrener SEO-Consultant. Tiefenanalyse: Führe ein umfassendes SEO-Audit für die folgende Website bzw. Seite durch und erkläre deine Kriterien. Berücksichtige aktuelle Anforderungen an AI-, GEO- und AEO-Optimierung. 

Die Inhalte stammen aus mehreren Seiten der Domain (Startseite + wichtige Unterseiten):
{contexts_combined}

Zusätzliche Daten:
📰 Aktuelle Branchentrends (RSS): {rss_snippets}
📈 Google Trends: {trends_insights}


Antwortstruktur:
- 🔍 Keywords & Suchintention:
- 🧠 Nutzerfokus (AIO, GEO, AEO):
- 📊 SERP-Analyse & Snippet-Potenzial:
- 📰 Relevanz aktueller Branchentrends:
- 🏧 Struktur & Lesbarkeit:
- 📜 Meta-Daten & CTA:
- ♿ Accessibility & Technik:
- 📍 Lokale Relevanz:
- 💡 Strategische Empfehlungen:
"""

Struktur der Analyse:

1. Meta & Snippet-Optimierung:
   - Title & Meta-Description: Relevanz, Länge, CTR-Potenzial
   - Strukturierte Daten (falls sichtbar)
   - SERP-Optimierung (z. B. für Featured Snippets)

2. Keyword-Analyse:
   - Hauptthema & Suchintention erkennen
   - Keyword-Cluster & semantische Erweiterungen

3. Content-Qualität:
   - E-E-A-T-Anmutung (Vertrauen, Autorität)
   - Duplicate, Thin Content oder Keyword Stuffing
   - Lesbarkeit & Mehrwert

4. Technische Struktur (Oberfläche):
   - H-Struktur (H1-H3)
   - Interne Verlinkung (sichtbar)
   - Ladezeit-Indikatoren (falls einschätzbar)

5. User Experience:
   - Aufbau, Scannability, Call-to-Actions
   - Mobilfreundlichkeit & visuelle Klarheit

6. Markt & Trends:
   - Relevante Themenlücken
   - Trendthemen integrierbar?

7. Nutzerzentrierung & LLM-Fokus:
   - AIO: Verständlichkeit & Gliederung für LLMs
   - GEO: Struktur & semantische Klarheit für Generative Engines
   - AEO: Eignung für Snippets, FAQ, direkte Antworten

8. Lokale SEO-Optimierung:


Antwortstruktur:
- 🔎 SEO-Fokus & Hauptthema:
- 🏷️ Meta-Elemente:
- 🔑 Keyword-Chancen:
- 📄 Content-Stärken & Schwächen:
- 🧱 Struktur- und Formatkritik:
- 👁️ UX & Lesefluss:
- 📊 Marktbezug & Trendchancen:
- Lokales SEO
- ✅ Priorisierte Optimierungsvorschläge:
"""

# 7. SEO-Optimierung
seo_optimization_prompt_fast = """
Du bist ein erfahrener SEO-Texter. Optimiere den folgenden Text für bessere Sichtbarkeit in Suchmaschinen - ohne die Lesbarkeit für Menschen zu beeinträchtigen. Gib auf Basis des folgenden SEO-Kontexts schnelle, konkrete Optimierungsvorschläge für eine bestimmte Seite **und allgemeine Tipps für andere Unterseiten**.


Zielseite:
{contexts_combined}

SEO-Audit-Zusammenfassung:
{seo_audit_summary}

Lighthouse-Report: 
{lighthouse_json}

Ziel:
- Keyword-Relevanz verbessern (natürlich eingebunden)
- Meta-Elemente (Title & Description) generieren
- Struktur und Lesbarkeit erhöhen (Überschriften, Absätze)
- E-E-A-T-Anmutung stärken (Vertrauen, Fachlichkeit)

Antwortstruktur:
=== ZIELSEITE ===
- ✍️ Keywords:
- Überarbeiteter Text:
- 🏗️ Struktur & H-Tags:
- 📜 Meta-Daten:
- 📣 CTAs:
- ⚙️ Technisches SEO:
- 📄 Verbesserungshinweise (stichpunktartig):

=== ANDERE UNTERSEITEN (generelle Tipps) ===
- 🔗 Interne Verlinkung:
- 🧭 Allgemeine Content-Tipps:
- 📍 Lokale Hinweise:
- 📄 Verbesserungshinweise (stichpunktartig):
"""

seo_optimization_prompt_deep = """
Du bist ein erfahrener SEO-Optimierer mit redaktioneller Erfahrung. Überarbeite den folgenden Text umfassend - mit dem Ziel, Sichtbarkeit und Relevanz in Suchmaschinen zu maximieren, ohne die Lesbarkeit für Menschen zu verlieren auf Basis der folgenden Eckdaten: 

Einleitende Mini-Analyse ist erlaubt (z. B. Keywords & Struktur prüfen), aber keine Vollanalyse wie im SEO-Audit.

Kontext:
- SEO-Audit-Zusammenfassung: {seo_audit_summary}
- Lighthouse-Report: {lighthouse_json}
- Inhalte mehrerer Seiten: {contexts_combined}
- Zielseite im Fokus: {focus_url}
- Branchentrends: {rss_snippets}
- Trend-Insights: {trends_insights}
- Markt-Daten: {destatis_stats}

### Vorgehen:
1. Thema & Suchintention erfassen
2. Text auf Keyword-Abdeckung & Synonyme prüfen
3. Meta-Elemente (Title + Description) optimieren
4. Struktur (Abschnitte, H-Tags) verbessern
5. Stil & Lesbarkeit optimieren (Absätze, klare Sprache)
6. Content-Stärke: Vertrauen, Fachwissen, Relevanz (E-E-A-T)
7. Optionale Trendintegration

Kategorien:
1. 🔍 Keywords & Suchintention
2. ✍️ Textqualität & Stil
3. 🏗️ Struktur & H-Tags
4. 📜 Meta-Daten & Snippets
5. 📣 CTA & Conversion
6. ⚙️ Technische SEO (Lighthouse)
7. 🔗 Interne Verlinkung
8. 🗂️ Unterseiten-Strategie
9. 📍 Lokales SEO
10. 🧭 Strategische Roadmap
11. 🧠 Trend-Relevanz & Marktpotenzial (Trends, RSS, DESTATIS)

### Antwortstruktur:
- 🏷️ Meta-Title (max. 60 Zeichen):
- 📝 Meta-Description (max. 155 Zeichen):
- 🔍 Keyword-Abdeckung & Cluster:
- 🧠 E-E-A-T-Stärkung:
- 🧪 Vorschläge für A/B-Tests oder Varianten:
"""

Antwortstruktur:
=== ZIELSEITE: {focus_url} ===
- Keywords & Suchintention:
  - Prio 1: [...], Begründung: [...]
  - Prio 2: [...], Begründung: [...]
- Neuer SEO-optimierter Text:
- Meta Informationen: 
- E-E-A-T-Stärkung:
- Andere Verbesserungsvorschläge:

=== GENERELLE TIPPS FÜR ANDERE SEITEN ===
- 🔗 Interne Verlinkung:
- 🧭 Allgemeine Content-Tipps:
- 📍 Lokale Hinweise:
- 📄 Verbesserungshinweise (stichpunktartig):
"""

# ===== Cluster 8: Technisches SEO =====

# 8. SEO-Optimierung

seo_lighthouse_prompt_fast = """
Du bist SEO-Analyst. Interpretiere die mit oder ohne der folgenden Lighthouse-Daten und gib eine kurze Bewertung zur SEO-Qualität der analysierten Seite ab.

Kontext:
{context_combined}

Lighthouse-Daten (SEO-Sektion):  
{lighthouse_data}

Antwortstruktur:
- 📊 SEO-Score: (Numerischer Wert + Kurzbewertung)
- ✅ Stärken der Seite (3 Bullet Points):
- ⚠️ Schwächen & Empfehlungen (max. 5 Bullet Points):
- 🧩 Technische Hinweise (falls relevant, z. B. Meta, Hreflang, Indexierung):
- 📍 Lokales SEO-Check:
- 🤖 SEO-LLM-Kriterien (AEO, GEO, AIO):
- 🧭 Nächste Schritte (konkret & priorisiert):
"""

seo_lighthouse_prompt_deep = """
Du bist ein technischer SEO-Analyst. 🧠 Tiefenanalyse: Verarbeite mehrere Lighthouse-Reports systematisch. Gib pro Seite eine Bewertung und dann eine Zusammenfassung mit globalen Empfehlungen. Nutze klare Kategorien, Prioritäten, Aufwand & Wirkung.

Input:
- {lighthouse_reports_combined}

Kontext:
{context_combined}

Ziel:
- Technische und strukturelle SEO-Schwächen aufdecken
- Suchmaschinen-Sichtbarkeit verbessern
- Umsetzbare Empfehlungen liefern (OnPage/OffPage)

Analysebereiche:
1. SEO-Score & allgemeine Bewertung
2. Meta-Tags & strukturierte Daten
3. Indexierung & Crawling-Hinweise
4. Linkstruktur, Canonical, hreflang
5. Mobile-Freundlichkeit & Performance-Faktoren
6. Lokales SEO (NAP, Standortdaten, GMaps, Schema.localBusiness)
7. SEO für LLMs: AEO (Answer), GEO (Entities), AIO (Intent)
7. Empfehlungen mit Priorisierung

Antwortstruktur:
- 📈 SEO-Score & Gesamturteil:
- ✅ Positive SEO-Signale:
- ⚠️ Kritische Schwächen (mit Ursachen):
- 🧱 Technische SEO-Hinweise:
- 🔧 Priorisierte Optimierungsschritte:
- 🧭 Langfristige Empfehlungen (für nachhaltiges Ranking):
"""


Antwortstruktur:
=== TECHNISCHE BEWERTUNG PRO SEITE ===
- /seite1:
  - 📈 SEO-Score & Gesamturteil:
  - ✅ Positive SEO-Signale:
  - ⚠️ Kritische Schwächen (mit Ursachen):
  - 🔧 Priorisierte Optimierungsschritte:

=== GESAMTBEWERTUNG & FAZIT ===
- 🔧 Wichtigste Probleme (aggregiert):
- 📋 Empfehlungen nach Kategorie mit:
  - Prio (1-3)
  - Aufwand (niedrig/mittel/hoch)
  - Wirkung (hoch/mittel/gering)
- 📍 Lokale Optimierungsmöglichkeiten:
- 🤖 SEO-Lens für KI-Suchergebnisse (AEO, GEO, AIO):
"""

# ===== Cluster 9: Reports & Maßnahmen =====

monthly_report_prompt_fast = """
Du bist Marketing-Analyst. Erstelle einen kompakten Monatsreport auf Basis der folgenden Daten.

Zeitraum: {monat}  
Inhalte & Kampagnen (Textauszug): {context}

Antwortstruktur:
- Zusammenfassung:
- Was hat funktioniert? (3 Bullet Points):
- Was war schwach oder überflüssig?
- Empfehlungen für Optimierung:
- Neue Content- oder Kampagnenideen:
- Trends oder externe Impulse, die relevant sind:
- Lokaler Kontext (optional):
- Bonus: KI-Einsatz / Automatisierungsideen:
"""

monthly_report_prompt_deep = """
Du bist Marketing-Stratege. Erstelle eine tiefgehende Monatsauswertung zur Content- und Kampagnenperformance.

📆 Zeitraum: {monat}  
📄 Inhalte, Maßnahmen & Kampagnen (Textauszug oder Zusammenfassung):  
{context}

Zusätzliche Datenquellen:
- 📰 Branchentrends: {rss_snippets}
- 📈 Google Trends: {trends_insights}
- 📊 Marktkennzahlen: {destatis_stats}

Ziele:
- Erfolge & Schwächen identifizieren
- Strategie und Inhalte bewerten
- Learnings & Empfehlungen für den nächsten Monat ableiten

Struktur der Antwort:
1. 🎯 Ziel- und Maßnahmenabgleich:
   - Was war geplant vs. umgesetzt?
   - Welche KPIs wurden erreicht?

2. 📊 Performance-Analyse:
   - Was hat gut funktioniert? (Erfolge, Hebel, Formate)
   - Was war unterdurchschnittlich oder überflüssig?

3. 💡 Strategie-Empfehlungen:
   - Welche Themen/Formate sollten fortgeführt werden?
   - Wo liegen ungenutzte Potenziale?

4. 📰 Trends & Markt-Reflexion:
   - Externe Einflüsse oder Themenverschiebungen
   - Passende Trends fürs nächste Monatsbriefing

Antwortstruktur:
- ✅ Erfolge & Highlights:
- ⚠️ Schwächen & Bottlenecks:
- 🔄 Empfehlungen (präzise & umsetzbar):
- 💡 Neue Ideen & Testansätze:
- 📰 Trendrelevanz & Marktanpassungen:
- Lokaler Kontext:
- Bonus: KI-Einsatz / Automatisierungsideen:

"""

# 10. Taktische Maßnahmen
tactical_actions_prompt_fast = """
Du bist Performance-Marketer. Leite konkrete, sofort umsetzbare Taktiken aus dem folgenden Input ab.

📄 Kontext (z. B. Analyse, Strategie, Audit):  
{context}

Ziel:
- Klar priorisierte Maßnahmen für Marketing, Content oder SEO
- Schnelle Umsetzung möglich (Quick Wins)

Antwortstruktur:
- 🚀 Quick Wins (3-5 Maßnahmen, sofort umsetzbar):
- 🔧 Mittelfristige Taktiken (nach Aufwand oder Hebel priorisiert):
- 💬 Kommentar: (optional, Kontext oder Hinweis zur Umsetzung)
- 📍 Lokale Maßnahmen:
- 📰 Offline-Materialien:
- 🤖 KI-Integration & Automatisierung:
"""


tactical_actions_prompt_deep = """
Du bist erfahrener Performance-Stratege. Leite aus dem folgenden Input konkrete, priorisierte Taktiken ab, die direkt in Maßnahmen überführt werden können (ein realistischer, priorisierter Maßnahmenplan).

Eingaben:
- SEO-Audit-Zusammenfassung: {seo_summary}
- Lighthouse-Report: {lighthouse_json}
- Wettbewerbsanalyse: {competitor_summary}
- Kampagnenplan: {campaign_plan}
- Branchentrends: {rss_snippets}
- Trend-Insights: {trends_insights}
- Markt-Daten: {destatis_stats}
- {context}

Ziel:
- Maßgeschneiderte Handlungsempfehlungen für Content, SEO, Kampagnen
- Klar priorisiert nach Hebel, Relevanz und Aufwand
- Umsetzbar für Marketing- oder Redaktionsteams
- Fokussierung auf Lokalität und strategische Nachhaltigkeit

Antwortstruktur:
- 🧩 Kontextzusammenfassung (1-2 Sätze):

✅ Sofort-Maßnahmen (0-4 Wochen):
- Maßnahme: [...], Priorität: [...], Aufwand: [...], Wirkung: [...]

🌟 Mittelfristige Aktionen (1-3 Monate):
- Maßnahme: [...], Priorität: [...], Aufwand: [...], Wirkung: [...]

🚀 Langfristige Maßnahmen (ab 3 Monaten):
- Maßnahme: [...], Priorität: [...], Aufwand: [...], Wirkung: [...]

📍 Lokale Maßnahmen:
- Maßnahme: [...], Ziel: [...], Geo-Bezug: [...], Priorität: [...]

📰 Offline-Materialien:
- Maßnahme: [...], Integration mit Online-Kampagnen: [...]

🤖 KI-Integration & Automatisierung:
- Maßnahme: [...], Tool/Plattform: [...], Wirkung: [...]

🧠 SWOT-Analyse:
- Stärken:
- Schwächen:
- Chancen:
- Risiken:
"""
