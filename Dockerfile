# --------------------------------------
# 1) Basis-Image
# --------------------------------------
FROM python:3.11-slim

# --------------------------------------
# 2) Arbeitsverzeichnis
# --------------------------------------
WORKDIR /app

# --------------------------------------
# 3) System-Updates & Abhängigkeiten
#    - Build-Tools für native Python-Pakete
#    - Libs für lxml/BeautifulSoup
#    - Chromium für Lighthouse
# --------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      curl \
      gnupg \
      chromium \
      libxml2-dev \
      libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------
# 4) Node.js & Lighthouse
# --------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g lighthouse && \
    rm -rf /var/lib/apt/lists/*

# Damit Lighthouse den installierten Chromium findet
ENV CHROME_PATH=/usr/bin/chromium

# --------------------------------------
# 5) Python-Abhängigkeiten installieren
#    (zuerst nur requirements.txt für Docker-Cache)
# --------------------------------------
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --------------------------------------
# 6) Projektdateien kopieren
# --------------------------------------
COPY . /app

# --------------------------------------
# 7) Ports für FastAPI & Streamlit
# --------------------------------------
EXPOSE 8000 8080

# --------------------------------------
# 8) Start-Script
# --------------------------------------
COPY launch.sh /app/launch.sh
RUN chmod +x /app/launch.sh

# Damit Python-Module im Container importierbar sind
ENV PYTHONPATH=/app

# --------------------------------------
# 9) Container-Start
# --------------------------------------
CMD ["/app/launch.sh"]
