# --------------------------------------
# 1) Basis-Image
# --------------------------------------
FROM python:3.11-slim

# --------------------------------------
# 2) Arbeitsverzeichnis
# --------------------------------------
WORKDIR /app

# --------------------------------------
# 3) System-Updates & Abhängigkeiten inkl. Node.js + Lighthouse
# --------------------------------------
RUN apt-get update && \
    apt-get install -y build-essential curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g lighthouse && \
    rm -rf /var/lib/apt/lists/*

# --------------------------------------
# 4) Projektdateien kopieren
# --------------------------------------
COPY . /app

# --------------------------------------
# 5) Python-Abhängigkeiten installieren
# --------------------------------------
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --------------------------------------
# 6) Ports für FastAPI & Streamlit (Streamlit via Railway auf 8080)
# --------------------------------------
EXPOSE 8000 8080

# --------------------------------------
# 7) Start-Script
# --------------------------------------
COPY launch.sh /app/launch.sh
RUN chmod +x /app/launch.sh

CMD ["/app/launch.sh"]
