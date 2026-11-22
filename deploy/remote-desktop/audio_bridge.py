from __future__ import annotations

import asyncio
import os
from contextlib import suppress

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

MIC_PIPE = "/run/pulse/mic.pipe"
SPEAKER_DEVICE = "jarvis_sink.monitor"
SPEAKER_RATE = 24000
SPEAKER_CHUNK_BYTES = 960  # 20 ms, mono signed 16-bit PCM

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
_mic_lock = asyncio.Lock()


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/mic")
async def microphone(websocket: WebSocket) -> None:
    await websocket.accept()
    if _mic_lock.locked():
        await websocket.close(code=1013, reason="Another microphone is already connected.")
        return

    async with _mic_lock:
        fd: int | None = None
        try:
            # module-pipe-source reads the FIFO; opening it for writing pairs
            # with that reader without modifying JARVIS's sounddevice code.
            fd = await asyncio.to_thread(os.open, MIC_PIPE, os.O_WRONLY)
            while True:
                payload = await websocket.receive_bytes()
                if not payload or len(payload) > 32768:
                    continue
                view = memoryview(payload)
                offset = 0
                while offset < len(view):
                    written = await asyncio.to_thread(os.write, fd, view[offset:])
                    if written <= 0:
                        raise RuntimeError("Microphone pipe closed.")
                    offset += written
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            print(f"[remote-audio] microphone bridge stopped: {exc}", flush=True)
            with suppress(Exception):
                await websocket.close(code=1011, reason="Microphone bridge stopped.")
        finally:
            if fd is not None:
                with suppress(OSError):
                    os.close(fd)


@app.websocket("/speaker")
async def speaker(websocket: WebSocket) -> None:
    await websocket.accept()
    process: asyncio.subprocess.Process | None = None
    try:
        process = await asyncio.create_subprocess_exec(
            "parec",
            "--device", SPEAKER_DEVICE,
            "--format=s16le",
            f"--rate={SPEAKER_RATE}",
            "--channels=1",
            "--raw",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        assert process.stdout is not None
        while True:
            chunk = await process.stdout.read(SPEAKER_CHUNK_BYTES)
            if not chunk:
                break
            await websocket.send_bytes(chunk)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        print(f"[remote-audio] speaker bridge stopped: {exc}", flush=True)
        with suppress(Exception):
            await websocket.close(code=1011, reason="Speaker bridge stopped.")
    finally:
        if process is not None and process.returncode is None:
            process.terminate()
            with suppress(Exception):
                await asyncio.wait_for(process.wait(), timeout=2)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
