#!/usr/bin/env python3
"""One-shot authenticated WebSocket handshake probe for the desktop VNC path.

This runs inside the Render container and tests the same Nginx route and
Basic-Auth boundary used by the noVNC iframe. It does not modify JARVIS.
"""
from __future__ import annotations

import base64
import os
import socket
import sys
import time

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "10000"))
PASSWORD = os.environ.get("JARVIS_REMOTE_PASSWORD", "")
ORIGIN = "https://jarvis-web-fgustakimiteste.onrender.com"
PATH = "/vncws/websockify"

if not PASSWORD:
    print("[VNC-PROBE] FAIL: JARVIS_REMOTE_PASSWORD is missing", flush=True)
    raise SystemExit(2)

token = base64.b64encode(f"jarvis:{PASSWORD}".encode("utf-8")).decode("ascii")
key = base64.b64encode(b"JARVIS-probe-key!").decode("ascii")

request = (
    f"GET {PATH} HTTP/1.1\r\n"
    f"Host: jarvis-web-fgustakimiteste.onrender.com\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    f"Origin: {ORIGIN}\r\n"
    "Sec-WebSocket-Version: 13\r\n"
    f"Sec-WebSocket-Key: {key}\r\n"
    "Sec-WebSocket-Protocol: binary\r\n"
    f"Authorization: Basic {token}\r\n"
    "\r\n"
).encode("ascii")

last_error = None
for attempt in range(1, 9):
    try:
        print(f"[VNC-PROBE] Attempt {attempt}: {PATH} through Nginx", flush=True)
        with socket.create_connection((HOST, PORT), timeout=5) as sock:
            sock.settimeout(5)
            sock.sendall(request)
            response = bytearray()
            while b"\r\n\r\n" not in response and len(response) < 8192:
                chunk = sock.recv(1)
                if not chunk:
                    break
                response += chunk
            header = response.decode("latin-1", errors="replace")
            status_line = header.splitlines()[0] if header else "NO RESPONSE"
            print(f"[VNC-PROBE] HTTP response: {status_line}", flush=True)
            if " 101 " not in status_line:
                print("[VNC-PROBE] FAIL: WebSocket upgrade was not accepted", flush=True)
                print(header[:2000], flush=True)
                raise RuntimeError("WebSocket upgrade did not return 101")
            if "Sec-WebSocket-Accept:" not in header:
                raise RuntimeError("101 response has no Sec-WebSocket-Accept header")
            print("[VNC-PROBE] PASS: authenticated WebSocket handshake returned 101", flush=True)
            # x11vnc sends its RFB protocol banner as the first WebSocket frame.
            try:
                frame_prefix = sock.recv(32)
                print(f"[VNC-PROBE] First VNC frame bytes: {frame_prefix[:16].hex()}", flush=True)
            except socket.timeout:
                print("[VNC-PROBE] WebSocket accepted; VNC banner not read before timeout", flush=True)
            raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as exc:
        last_error = exc
        print(f"[VNC-PROBE] Attempt failed: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(1)

print(f"[VNC-PROBE] FAIL after retries: {last_error}", flush=True)
raise SystemExit(1)
