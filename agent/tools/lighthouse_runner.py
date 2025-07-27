# agent/tools/lighthouse_runner.py

import os
import json
import subprocess
from urllib.parse import urlparse

def run_lighthouse(raw_url: str) -> dict:
    """
    Führt das node-Script run_lighthouse.mjs mit der gegebenen URL aus
    und gibt das JSON-Resultat zurück. 
    Liefert bei jedem Fehler ein leeres Dict.
    """
    if not raw_url:
        return {}

    # 1) URL normalisieren: https:// voranstellen, wenn nötig
    parsed = urlparse(raw_url)
    if not parsed.scheme:
        url = "https://" + raw_url
    else:
        url = raw_url

    # Pfad zum .mjs-Script in diesem Package
    script = os.path.join(os.path.dirname(__file__), "run_lighthouse.mjs")
    report_file = os.path.join(os.getcwd(), "report.json")

    cmd = ["node", script, url, report_file]
    try:
        # Ausführen
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # JSON einlesen
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    except subprocess.CalledProcessError as e:
        # Für Debug: stdout/stderr in Log schreiben
        print("Lighthouse stdout:", e.stdout)
        print("Lighthouse stderr:", e.stderr)
        return {}

    except Exception as e:
        print(f"Lighthouse unexpected error: {e}")
        return {}
