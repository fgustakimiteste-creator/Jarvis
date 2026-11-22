#!/usr/bin/env python3
"""One-shot VNC and authenticated noVNC WebSocket diagnostic."""
from __future__ import annotations

import base64
import os
import socket
import time

HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "10000"))
PASSWORD = os.environ.get("JARVIS_REMOTE_PASSWORD", "")
ORIGIN = "https://jarvis-web-fgustakimiteste.onrender.com"
PATH = "/vncws/websockify"

def recv_exact(sock: socket.socket, size: int) -> bytes:
    data = bytearray()
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise ConnectionError(f"socket closed after {len(data)} of {size} bytes")
        data.extend(part)
    return bytes(data)

def raw_rfb_probe() -> None:
    print("[VNC-PROBE] Testing raw RFB server on 127.0.0.1:5900", flush=True)
    with socket.create_connection((HOST, 5900), timeout=4) as sock:
        sock.settimeout(4)
        banner = recv_exact(sock, 12)
        print(f"[VNC-PROBE] Raw RFB banner: {banner!r}", flush=True)
        if not banner.startswith(b"RFB "):
            raise RuntimeError(f"Unexpected raw VNC banner: {banner!r}")
        print("[VNC-PROBE] PASS: x11vnc speaks RFB on localhost:5900", flush=True)

def websocket_probe(host: str, port: int, path: str, authorization: str | None, label: str) -> None:
    print(f"[VNC-PROBE] Testing WebSocket at {host}:{port}{path} ({label})", flush=True)
    key = base64.b64encode(b"0123456789abcdef").decode("ascii")
    headers = [
        f"GET {path} HTTP/1.1",
        "Host: jarvis-web-fgustakimiteste.onrender.com",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Origin: {ORIGIN}",
        "Sec-WebSocket-Version: 13",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Protocol: binary",
    ]
    if authorization:
        headers.append(f"Authorization: Basic {authorization}")
    request = ("\r\n".join(headers) + "\r\n\r\n").encode("ascii")

    with socket.create_connection((host, port), timeout=4) as sock:
        sock.settimeout(4)
        sock.sendall(request)
        response = bytearray()
        while b"\r\n\r\n" not in response and len(response) < 8192:
            chunk = sock.recv(1)
            if not chunk:
                break
            response.extend(chunk)
        header = response.decode("latin-1", errors="replace")
        status = header.splitlines()[0] if header else "NO RESPONSE"
        print(f"[VNC-PROBE] {label} HTTP response: {status}", flush=True)
        if " 101 " not in status:
            print(header[:2000], flush=True)
            raise RuntimeError(f"{label} WebSocket upgrade did not return 101")
        if "Sec-WebSocket-Accept:" not in header:
            raise RuntimeError(f"{label} 101 response omitted Sec-WebSocket-Accept")
        print(f"[VNC-PROBE] PASS: {label} WebSocket handshake accepted", flush=True)

        # A VNC server must send an RFB version banner as its first WebSocket
        # binary frame. Decode the frame to verify more than the HTTP 101.
        first = recv_exact(sock, 2)
        opcode = first[0] & 0x0F
        length = first[1] & 0x7F
        if length == 126:
            length = int.from_bytes(recv_exact(sock, 2), "big")
        elif length == 127:
            length = int.from_bytes(recv_exact(sock, 8), "big")
        if first[1] & 0x80:
            mask = recv_exact(sock, 4)
        else:
            mask = None
        if length > 4096:
            raise RuntimeError(f"Unusually large initial VNC frame ({length} bytes)")
        payload = recv_exact(sock, length)
        if mask:
            payload = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        print(f"[VNC-PROBE] {label} first WebSocket frame opcode={opcode}, payload={payload!r}", flush=True)
        if opcode != 2 or not payload.startswith(b"RFB "):
            raise RuntimeError(f"{label} did not deliver an RFB banner in the first frame")
        print(f"[VNC-PROBE] PASS: {label} delivered the RFB banner", flush=True)

if not PASSWORD:
    print("[VNC-PROBE] FAIL: JARVIS_REMOTE_PASSWORD is missing", flush=True)
    raise SystemExit(2)

token = base64.b64encode(f"jarvis:{PASSWORD}".encode("utf-8")).decode("ascii")
checks = [
    ("x11vnc native WebSocket", lambda: websocket_probe(HOST, 5900, "/websockify", None, "x11vnc native")),
    ("Nginx authenticated", lambda: websocket_probe(HOST, PORT, PATH, token, "Nginx authenticated")),
]
failed = False
for label, check in checks:
    try:
        check()
    except Exception as exc:
        failed = True
        print(f"[VNC-PROBE] FAIL: {label}: {type(exc).__name__}: {exc}", flush=True)
    time.sleep(0.4)

if failed:
    print("[VNC-PROBE] DIAGNOSTIC FAILED: at least one VNC layer did not pass.", flush=True)
    raise SystemExit(1)

print("[VNC-PROBE] ALL CHECKS PASSED: RFB + websockify + authenticated Nginx", flush=True)
