# scheduler.py

from apscheduler.schedulers.blocking import BlockingScheduler
from scraper_pipeline import scrape_and_upload
from loguru import logger

logger.add("logs/agent.log", rotation="1 MB", retention="7 days")

scheduler = BlockingScheduler()

# Starte jeden Montag um 10:00 UTC (Deutschland = 12:00 im Sommer)
@scheduler.scheduled_job('cron', day_of_week='mon', hour=10, minute=0)
def weekly_scrape():
    url = "https://example.com"
    logger.info("🗓️ Wöchentlicher Scraper startet...")
    scrape_and_upload(url)

if __name__ == "__main__":
    logger.info("🚀 Scheduler läuft… (Ctrl+C zum Beenden)")
    scheduler.start()
