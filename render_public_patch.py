from __future__ import annotations

import re
from pathlib import Path


ROOT = Path("/opt/jarvis")


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Patch point expected once in {path}, found {count}: {old[:90]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


# Per-browser SQLite isolation. The original ZIP and its local/desktop behaviour
# remain unchanged; this adapter is applied only to the cloud container image.
db = ROOT / "app" / "database.py"
replace_once(
    db,
    "import sqlite3\n",
    "import sqlite3\nfrom contextvars import ContextVar\nfrom hashlib import sha256\n",
)
replace_once(
    db,
    "from .config import settings\n\n\ndef _connect() -> sqlite3.Connection:\n    settings.database_path.parent.mkdir(parents=True, exist_ok=True)\n    conn = sqlite3.connect(settings.database_path, timeout=10)",
    "from .config import settings\n\n"
    "_SESSION_KEY: ContextVar[str] = ContextVar(\"jarvis_session_key\", default=\"\")\n\n"
    "def set_session_key(value: str):\n    return _SESSION_KEY.set(value)\n\n"
    "def reset_session_key(token) -> None:\n    _SESSION_KEY.reset(token)\n\n"
    "def _connect() -> sqlite3.Connection:\n"
    "    session_key = _SESSION_KEY.get()\n"
    "    if session_key:\n"
    "        digest = sha256(session_key.encode(\"utf-8\")).hexdigest()[:32]\n"
    "        database_path = settings.database_path.parent / \"sessions\" / digest / settings.database_path.name\n"
    "    else:\n"
    "        database_path = settings.database_path\n"
    "    database_path.parent.mkdir(parents=True, exist_ok=True)\n"
    "    conn = sqlite3.connect(database_path, timeout=10)",
)

main = ROOT / "app" / "main.py"
source = main.read_text(encoding="utf-8")
source = source.replace(
    "import logging\n",
    "import logging\nimport os\nimport re\nfrom secrets import token_urlsafe\n",
    1,
)
source = source.replace(
    "from .database import add_message, clear_conversation, delete_memory, init_db, list_memories, recent_messages, save_memory",
    "from .database import (add_message, clear_conversation, delete_memory, init_db, list_memories, "
    "recent_messages, save_memory, set_session_key, reset_session_key)",
    1,
)
if "set_session_key" not in source or "import token_urlsafe" not in source:
    raise RuntimeError("Could not add public session imports")
source = source.replace(
    'STATIC_DIR = ROOT_DIR / "static"\n',
    'STATIC_DIR = ROOT_DIR / "static"\n'
    '_PUBLIC_MODE = os.getenv("JARVIS_PUBLIC_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}\n\n'
    '@app.middleware("http")\n'
    'async def public_session_isolation(request, call_next):\n'
    '    if not _PUBLIC_MODE:\n'
    '        return await call_next(request)\n'
    '    session_id = request.cookies.get("jarvis_sid", "")\n'
    '    if not re.fullmatch(r"[A-Za-z0-9_-]{32,80}", session_id):\n'
    '        session_id = token_urlsafe(32)\n'
    '    context_token = set_session_key(session_id)\n'
    '    try:\n'
    '        init_db()\n'
    '        response = await call_next(request)\n'
    '    finally:\n'
    '        reset_session_key(context_token)\n'
    '    response.set_cookie("jarvis_sid", session_id, max_age=2592000, httponly=True, secure=True, samesite="lax", path="/")\n'
    '    response.headers["Cache-Control"] = "no-store"\n'
    '    return response\n',
    1,
)
source = source.replace(
    '"ai_configured": bool(settings.gemini_api_key),',
    '"ai_configured": bool(settings.gemini_api_key), "public_mode": _PUBLIC_MODE,',
    1,
)
source = source.replace('"network_available": network_available,', '"network_available": network_available and not _PUBLIC_MODE,', 1)
source = source.replace('"local_network_discovery": network_available,', '"local_network_discovery": network_available and not _PUBLIC_MODE,', 1)
source = source.replace('"lan_port_diagnostics": True,', '"lan_port_diagnostics": not _PUBLIC_MODE,', 1)

route_guards = [
    ("def network_overview(_: None = Depends(require_token)) -> dict[str, Any]:\n",
     "def network_overview(_: None = Depends(require_token)) -> dict[str, Any]:\n    if _PUBLIC_MODE: raise HTTPException(status_code=403, detail=\"Scanner LAN disponível somente na instalação local do JARVIS.\")\n"),
    ("async def network_scan(_: None = Depends(require_token)) -> dict[str, Any]:\n",
     "async def network_scan(_: None = Depends(require_token)) -> dict[str, Any]:\n    if _PUBLIC_MODE: raise HTTPException(status_code=403, detail=\"Scanner LAN disponível somente na instalação local do JARVIS.\")\n"),
    ("def network_ports(payload: PortScanRequest, _: None = Depends(require_token)) -> dict[str, Any]:\n",
     "def network_ports(payload: PortScanRequest, _: None = Depends(require_token)) -> dict[str, Any]:\n    if _PUBLIC_MODE: raise HTTPException(status_code=403, detail=\"Diagnóstico LAN disponível somente na instalação local do JARVIS.\")\n"),
    ("def router_panel(_: None = Depends(require_token)) -> dict[str, Any]:\n",
     "def router_panel(_: None = Depends(require_token)) -> dict[str, Any]:\n    if _PUBLIC_MODE: raise HTTPException(status_code=403, detail=\"O painel do roteador só pode ser aberto no computador local.\")\n"),
]
for old, new in route_guards:
    if source.count(old) != 1:
        raise RuntimeError(f"Could not locate route guard: {old[:80]!r}")
    source = source.replace(old, new, 1)
main.write_text(source, encoding="utf-8")

# Prevent commands from opening a browser on the remote Render machine.
platform = ROOT / "app" / "platform_tools.py"
replace_once(
    platform,
    "def open_website(url: str) -> str:\n    raw = url.strip()",
    "def open_website(url: str) -> str:\n"
    "    if os.getenv(\"JARVIS_PUBLIC_MODE\", \"false\").strip().lower() in {\"1\", \"true\", \"yes\", \"on\"}:\n"
    "        return \"Esta instância está hospedada na nuvem. Abra o site diretamente no seu navegador; o JARVIS público não controla o navegador do servidor. \"\n"
    "    raw = url.strip()",
)

# The LAN scanner must never probe the hosting provider's private network.
network = ROOT / "app" / "network_tools.py"
net = network.read_text(encoding="utf-8")
if "import os\n" not in net:
    net = net.replace("from __future__ import annotations\n", "from __future__ import annotations\n\nimport os\n", 1)
net = net.replace(
    'def get_network_context() -> dict[str, Any]:\n    """Return only private IPv4 networks on active local interfaces."""\n',
    'def get_network_context() -> dict[str, Any]:\n    """Return only private IPv4 networks on active local interfaces."""\n'
    '    if os.getenv("JARVIS_PUBLIC_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}:\n'
    '        raise RuntimeError("O scanner de rede local funciona somente quando o JARVIS roda no seu próprio computador.")\n',
    1,
)
net = net.replace(
    "async def scan_local_network() -> dict[str, Any]:\n    global _LAST_SCAN\n",
    "async def scan_local_network() -> dict[str, Any]:\n    global _LAST_SCAN\n"
    '    if os.getenv("JARVIS_PUBLIC_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}:\n'
    '        raise RuntimeError("O scanner de rede local funciona somente quando o JARVIS roda no seu próprio computador.")\n',
    1,
)
net = net.replace(
    "def scan_device_ports(target_ip: str) -> dict[str, Any]:\n",
    "def scan_device_ports(target_ip: str) -> dict[str, Any]:\n"
    '    if os.getenv("JARVIS_PUBLIC_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}:\n'
    '        raise RuntimeError("O diagnóstico de portas LAN só funciona na instalação local do JARVIS.")\n',
    1,
)
if "O scanner de rede local funciona somente" not in net or "import os" not in net:
    raise RuntimeError("Could not apply public LAN safety restrictions")
network.write_text(net, encoding="utf-8")

# Improve the status label in the existing interface, when its original text matches.
ui = ROOT / "static" / "app.js"
js = ui.read_text(encoding="utf-8")
js = re.sub(
    r"\$\('authState'\)\.textContent = status\.token_required \? ('[^']+') : 'Somente local';",
    r"$('authState').textContent = status.token_required ? 'Token obrigatório' : (status.public_mode ? 'Sessão isolada' : 'Somente local');",
    js,
    count=1,
)
ui.write_text(js, encoding="utf-8")

print("Public Render adapter applied: per-browser sessions, no shared history, LAN scanner disabled in cloud mode.")
