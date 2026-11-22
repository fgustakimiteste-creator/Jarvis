FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000 \
    JARVIS_ENV=production \
    ALLOW_EPHEMERAL_SQLITE_PRODUCTION=1 \
    DATABASE_URL=sqlite:////app/tmp/jarvis_web.db \
    REDIS_REQUIRED=0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        unzip build-essential libglib2.0-0 libgl1 libportaudio2 portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

COPY JARVIS-OS-V.2-main.zip /tmp/jarvis.zip
COPY render_v2_patch.py /tmp/render_v2_patch.py

RUN mkdir -p /tmp/jarvis-source /app/tmp \
    && unzip -q /tmp/jarvis.zip -d /tmp/jarvis-source \
    && test -f /tmp/jarvis-source/JARVIS-OS-V.2-main/api/server.py \
    && test -f /tmp/jarvis-source/JARVIS-OS-V.2-main/web/package.json \
    && cp -a /tmp/jarvis-source/JARVIS-OS-V.2-main/. /app/ \
    && python /tmp/render_v2_patch.py \
    && python -m pip install --upgrade pip \
    && python -m pip install -r /app/requirements.txt \
    && chmod +x /app/scripts/start_web_api.sh \
    && useradd --system --uid 10001 jarvis \
    && chown -R jarvis:jarvis /app \
    && rm -rf /tmp/jarvis-source /tmp/jarvis.zip /tmp/render_v2_patch.py

USER jarvis

EXPOSE 10000
CMD ["./scripts/start_web_api.sh"]
