# pipeline_upload.py

import json
from datetime import datetime
from storage import upload_file
from loguru import logger

# Loguru-Setup: einfach
logger.add("logs/agent.log", rotation="1 MB", retention="7 days")

def store_results_locally_and_upload(result_data: dict, prefix: str = "results"):
    """
    Speichert ein Ergebnis lokal als JSON und lädt es danach in deinen S3-Bucket hoch.
    """

    # Erstelle Dateinamen mit Timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    local_file = f"data/{prefix}_{timestamp}.json"
    s3_key = f"{prefix}/{prefix}_{timestamp}.json"

    # Speichern lokal
    with open(local_file, "w") as f:
        json.dump(result_data, f, indent=2)

    logger.info(f"📄 Ergebnis lokal gespeichert: {local_file}")

    # Hochladen
    upload_file(local_file, s3_key)
    logger.info(f"✅ Ergebnis in S3 hochgeladen: {s3_key}")

# --- Mini-Test ---
if __name__ == "__main__":
    dummy_result = {
        "text": "Dies ist ein Dummy-Ergebnis deines Scrapers.",
        "timestamp": datetime.utcnow().isoformat()
    }
    store_results_locally_and_upload(dummy_result)
