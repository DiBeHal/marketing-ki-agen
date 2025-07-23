from agent.base_agent import run_agent

url = "https://example.com"  # oder jede echte Kunden-URL

print("⏳ Starte technische SEO-Analyse mit Lighthouse...\n")
antwort = run_agent(mode="seo_lighthouse", url=url)

print("\n📊 GPT-Analyse des SEO-Reports:\n")
print(antwort)
