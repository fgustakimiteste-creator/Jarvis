# JARVIS remote desktop deployment

This infrastructure layer runs the original PyQt6 desktop application from the unchanged ZIP:
- `main.py` launches `ui.py` and its original MainWindow/HUD/Mission Control.
- Xvfb provides a virtual 1280x820 display.
- TigerVNC's X0tigervnc scrapes that display and serves plain RFB over localhost.
- noVNC displays the desktop in the browser; Nginx forwards the WebSocket Upgrade to websockify, which translates it to plain RFB for TigerVNC.
- The browser microphone and speaker toolbar forwards PCM to/from PulseAudio through an isolated WebSocket bridge.
- Nginx Basic Auth protects the page, VNC WebSocket, and audio sockets. The browser WebSocket is terminated by websockify and forwarded as standard RFB to the localhost-only TigerVNC server.

The source ZIP and all original app files remain unchanged. The browser toolbar is outside the PyQt window and does not replace its screens or components.

## Access
- Username: `jarvis`
- Password: private Render variable `JARVIS_REMOTE_PASSWORD`.
- Health: `/healthz`.

## Browser audio
Click **Ativar microfone** and grant browser permission. Click **Ouvir JARVIS** to hear the original application's audio output. The virtual PulseAudio source/sink feeds the stock `sounddevice.InputStream` and `sounddevice.RawOutputStream` in `main.py`; the application code itself is not patched.

## Important runtime boundary
The PyQt app runs inside the Render container. The browser microphone/speaker are bridged, but computer-control, local file, screen-capture, process, and LAN actions operate on the container, not the visitor's PC. To operate the actual local Windows/macOS/Linux desktop, run the original JARVIS app on that computer (or build/install a separately trusted local agent). A browser-only link cannot grant the remote server access to a visitor's OS.

The free Render service has 512 MB RAM, ephemeral filesystem, no persistent disk, and can restart or sleep. The original UI key entry is session-only unless the user opts into an OS keychain; therefore a restart can require entering the Gemini key again. The first deploy should be treated as a technical test, not persistent production hosting.
