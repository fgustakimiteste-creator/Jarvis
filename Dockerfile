FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    JARVIS_PUBLIC_MODE=true \
    JARVIS_HOST=0.0.0.0 \
    JARVIS_PORT=10000 \
    JARVIS_DB_PATH=/opt/jarvis/data/jarvis.db

WORKDIR /opt/jarvis
COPY JARVIS_OS_V4_1.zip /tmp/jarvis.zip
COPY render_public_patch.py /tmp/render_public_patch.py

RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip \
    && mkdir -p /tmp/jarvis-src /opt/jarvis/data \
    && unzip -q /tmp/jarvis.zip -d /tmp/jarvis-src \
    && cp -a /tmp/jarvis-src/JARVIS/. /opt/jarvis/ \
    && python /tmp/render_public_patch.py \
    && python -m compileall -q /opt/jarvis/app \
    && python -m pip install --upgrade pip \
    && python -m pip install -r /opt/jarvis/requirements.txt \
    && rm -rf /var/lib/apt/lists/* /tmp/jarvis-src /tmp/jarvis.zip /tmp/render_public_patch.py \
    && useradd --system --uid 10001 jarvis \
    && chown -R jarvis:jarvis /opt/jarvis

USER jarvis
EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
