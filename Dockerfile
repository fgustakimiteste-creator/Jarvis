FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /opt/jarvis
COPY Jarvis_OS_v4_3_Public_Ready.zip /tmp/jarvis.zip

RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip \
    && mkdir -p /tmp/jarvis-src /opt/jarvis/data /opt/jarvis/workspace \
    && unzip -q /tmp/jarvis.zip -d /tmp/jarvis-src \
    && cp -a /tmp/jarvis-src/Jarvis/. /opt/jarvis/ \
    && python -m pip install --upgrade pip \
    && python -m pip install -r /opt/jarvis/requirements.txt \
    && rm -rf /var/lib/apt/lists/* /tmp/jarvis-src /tmp/jarvis.zip \
    && useradd --system --uid 10001 jarvis \
    && chown -R jarvis:jarvis /opt/jarvis

USER jarvis
EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
