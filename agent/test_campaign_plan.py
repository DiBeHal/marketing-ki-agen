# test_campaign_plan.py

from agent.base_agent import run_agent
from agent.loader import load_pdf

# 🔄 Beliebige Datei verwenden
text = load_pdf("testkampagne.pdf")

result = run_agent(mode="campaign_plan", text=text)

print("\n📢 Kampagnenplan:\n")
print(result)
