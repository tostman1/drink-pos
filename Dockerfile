FROM python:3.12-slim

ARG BUILD_COMMIT=unknown
ARG BUILD_REF=unknown
ARG BUILD_CHANNEL=unknown
ARG BUILD_TAGS=

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DRINK_POS_ENV=production \
    DRINK_POS_DB=/app/data/drink_pos.db \
    DRINK_POS_BACKUP_DIR=/app/data/backups \
    APP_BUILD_COMMIT=${BUILD_COMMIT} \
    APP_BUILD_REF=${BUILD_REF} \
    APP_BUILD_CHANNEL=${BUILD_CHANNEL} \
    APP_BUILD_TAGS=${BUILD_TAGS}

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY app/ /app/

RUN mkdir -p /app/data/backups

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
