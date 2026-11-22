from __future__ import annotations

import asyncio
import os
from contextlib import suppress

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

MIC_PIPE = "/run/pulse/mic.pipe"
MIC_INPUT_RATE = 16000
MIC_PIPE_RATE = 44100
SPEAKER_DEVICE = "jarvis_sink.monitor"
SPEAKER_RATE = 24000
SPEAKER_CHUNK_BYTES = 960  # 20 ms, mono signed 16-bit PCM

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
_mic_lock = asyncio.Lock()


@app.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _to_pulse_pipe(payload: bytes) -> bytes:
    """Convert browser 16 kHz mono PCM into PulseAudio pipe-source defaults."""
    mono = np.frombuffer(payload, dtype="<i2")
    if mono.size == 0:
        return b""
    out_count = max(1, round(mono.size * MIC_PIPE_RATE / MIC_INPUT_RATE))
    positions = np.arange(out_count, dtype=np.float64) * (MIC_INPUT_RATE / MIC_PIPE_RATE)
    source_positions = np.arange(mono.size, dtype=np.float64)
    resampled = np.interp(
        positions,
        source_positions,
        mono.astype(np.float64),
        left=float(mono[0]),
        right=float(mono[-1]),
    )
    pcm = np.clip(np.rint(resampled), -32768, 32767).astype("<i2")
    stereo = np.repeat(pcm[:, None], 2, axis=1)
    return stereo.reshape(-1).tobytes()


@app.websocket("/mic")
async def microphone(websocket: WebSocket) -> None:
    await websocket.accept()
    if _mic_lock.locked():
        await websocket.close(code=1013, reason="Another microphone is already connected.")
        return

    async with _mic_lock:
        fd: int | None = None
        try:
            # module-pipe-source reads this FIFO as 44.1 kHz stereo s16le.
            # JARVIS's unmodified sounddevice input stream requests 16 kHz mono;
            # ALSA's PulseAudio plugin performs the final per-stream resampling.
            fd = await asyncio.to_thread(os.open, MIC_PIPE, os.O_WRONLY)
            while True:
                payload = await websocket.receive_bytes()
                if not payload or len(payload) > 32768 or len(payload) % 2:
                    continue
                converted = await asyncio.to_thread(_to_pulse_pipe, payload)
                view = memoryview(converted)
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
