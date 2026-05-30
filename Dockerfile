FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/data

WORKDIR /app

# app lives in oakridge-drawings-site/ ; build from repo root so Coolify needs
# no "base directory" configuration
COPY oakridge-drawings-site/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY oakridge-drawings-site/ .

RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/healthz').read()" || exit 1

CMD ["sh", "-c", "gunicorn -w 2 -t 300 -b 0.0.0.0:${PORT} app:app"]
