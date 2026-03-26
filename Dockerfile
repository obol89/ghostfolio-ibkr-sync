FROM python:3.12-slim

WORKDIR /app

# Install supercronic for cron support
ARG SUPERCRONIC_VERSION=v0.2.33
ARG SUPERCRONIC_SHA256=71b0d58cc53f6bd72f4571b3c34dc4c0c9295cc09d04b4b64fc138bf4ef070e2
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSLO "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-amd64" && \
    echo "${SUPERCRONIC_SHA256}  supercronic-linux-amd64" | sha256sum -c - && \
    chmod +x supercronic-linux-amd64 && \
    mv supercronic-linux-amd64 /usr/local/bin/supercronic && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ibkr_to_ghostfolio.py .

# Default mount point for the mapping file
VOLUME ["/app/mapping.yaml"]

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
