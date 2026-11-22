#!/bin/sh
set -eu

: "${JARVIS_REMOTE_PASSWORD:?JARVIS_REMOTE_PASSWORD must be set as a private Render environment variable}"
htpasswd -bc /etc/nginx/.htpasswd jarvis "$JARVIS_REMOTE_PASSWORD" >/dev/null
chmod 640 /etc/nginx/.htpasswd
envsubst '${PORT}' < /etc/nginx/templates/jarvis.conf.template > /etc/nginx/conf.d/default.conf
nginx -t
exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
