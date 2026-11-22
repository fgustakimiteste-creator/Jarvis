#!/bin/sh
set -eu

: "${JARVIS_REMOTE_PASSWORD:?Configure JARVIS_REMOTE_PASSWORD as a private Render environment variable}"

mkdir -p /run/remote /run/pulse
htpasswd -Bbc /etc/nginx/.htpasswd jarvis "$JARVIS_REMOTE_PASSWORD" >/dev/null
chmod 640 /etc/nginx/.htpasswd
x11vnc -storepasswd "$JARVIS_REMOTE_PASSWORD" /run/remote/vnc.pass >/dev/null
chmod 600 /run/remote/vnc.pass
chown jarvis:jarvis /run/remote/vnc.pass
envsubst '${PORT}' < /etc/nginx/templates/jarvis.conf.template > /etc/nginx/conf.d/default.conf
nginx -t

exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
