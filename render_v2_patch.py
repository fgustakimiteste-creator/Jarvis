from pathlib import Path

def replace_function(path: Path, start_marker: str, end_marker: str, replacement: str) -> None:
    source = path.read_text(encoding="utf-8")
    start = source.find(start_marker)
    end = source.find(end_marker, start + len(start_marker))
    if start < 0 or end < 0:
        raise RuntimeError(f"Could not find expected function markers in {path}")
    path.write_text(source[:start] + replacement.rstrip() + "\n\n" + source[end:], encoding="utf-8")


config = Path("/app/api/config.py")
source = config.read_text(encoding="utf-8")
old = '''        if not self.database_url.startswith(("postgresql://", "postgres://", "postgresql+")):
            raise RuntimeError("Production DATABASE_URL must point to Postgres")'''
new = '''        is_postgres = self.database_url.startswith(("postgresql://", "postgres://", "postgresql+"))
        allow_ephemeral_sqlite = os.environ.get("ALLOW_EPHEMERAL_SQLITE_PRODUCTION", "0").strip().lower() in {
            "1", "true", "yes", "on",
        }
        is_ephemeral_sqlite = allow_ephemeral_sqlite and self.database_url.startswith("sqlite:///")
        if not (is_postgres or is_ephemeral_sqlite):
            raise RuntimeError("Production DATABASE_URL must point to Postgres unless ephemeral SQLite is explicitly enabled")'''
if source.count(old) != 1:
    raise RuntimeError("Could not find the expected production database validation block.")
config.write_text(source.replace(old, new, 1), encoding="utf-8")
print("Enabled explicitly opted-in ephemeral SQLite for the Render free-tier API.")

validator = Path("/app/core/api_key_validator.py")
validator_function = r'''def _validate_with_gemini(api_key: str, timeout_seconds: float) -> ApiKeyValidationResult:
    """Verify the key and probe the actual Live WebSocket, not only models.list metadata."""
    import asyncio
    import os

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                api_version="v1beta",
                timeout=max(1000, int(timeout_seconds * 1000)),
            ),
        )

        # models.list is useful for discovery, but it is not an authoritative
        # permission check for opening a Gemini Live session.
        try:
            listed_models = list(client.models.list())
        except Exception:
            listed_models = []

        def model_name(model) -> str:
            return str(getattr(model, "name", "") or "").strip()

        def model_actions(model) -> set[str]:
            actions = getattr(model, "supported_actions", None)
            if actions is None:
                actions = getattr(model, "supportedActions", None)
            return {str(action).lower() for action in (actions or [])}

        live_models = [
            model_name(model)
            for model in listed_models
            if "bidigeneratecontent" in model_actions(model) and model_name(model)
        ]

        def score(name: str) -> tuple[int, str]:
            lowered = name.lower()
            if "native-audio" in lowered:
                return (0, name)
            if "live" in lowered:
                return (1, name)
            if "flash" in lowered:
                return (2, name)
            return (3, name)

        configured = (
            os.environ.get("GEMINI_LIVE_MODEL", "").strip()
            or "models/gemini-2.5-flash-native-audio-preview-12-2025"
        )
        candidates = sorted(set(live_models), key=score)
        if configured not in candidates:
            candidates.append(configured)

        async def probe_candidates():
            errors = []
            for model in candidates[:3]:
                try:
                    config = types.LiveConnectConfig(response_modalities=["AUDIO"])
                    async with asyncio.timeout(timeout_seconds):
                        async with client.aio.live.connect(
                            model=model.removeprefix("models/"),
                            config=config,
                        ):
                            # setupComplete proves that a real Live session can
                            # be opened. No user prompt or audio is transmitted.
                            return model, None
                except Exception as exc:
                    errors.append(f"{model}: {str(exc).strip() or exc.__class__.__name__}")
            return None, errors

        selected_model, errors = asyncio.run(probe_candidates())
        if selected_model:
            return ApiKeyValidationResult(
                True,
                f"Gemini API key and Live access verified ({selected_model.removeprefix('models/')}).",
            )

        detail = errors[-1] if errors else "No Live model could be probed."
        lowered = detail.lower()

        if "api key not valid" in lowered or "invalid api key" in lowered or "api_key_invalid" in lowered:
            return ApiKeyValidationResult(False, "API key is not valid.")
        if "unauthenticated" in lowered or "401" in lowered:
            return ApiKeyValidationResult(False, "Gemini rejected this API key during the Live connection.")
        if "1008" in lowered or "project has been denied access" in lowered or "denied access" in lowered:
            return ApiKeyValidationResult(
                False,
                "Gemini accepted the key, but Google denied Live API access for this project (1008). Check the project status and Live access in Google AI Studio.",
            )
        if "permission" in lowered or "403" in lowered:
            return ApiKeyValidationResult(
                False,
                "Gemini accepted the key, but this project/key does not have permission to open a Live session. Check the key type, project permissions, and API restrictions in Google AI Studio.",
            )
        if "not found" in lowered or "not supported" in lowered:
            return ApiKeyValidationResult(
                False,
                "The key was accepted, but the configured Live model is not available to this project. Check the Live model selected for JARVIS.",
            )
        return ApiKeyValidationResult(
            False,
            f"Gemini key could not open a Live session. Check project access and connection, then try again. ({detail[:160]})",
        )
    except Exception as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        lowered = detail.lower()
        if "api key not valid" in lowered or "invalid api key" in lowered:
            return ApiKeyValidationResult(False, "API key is not valid.")
        if "unauthenticated" in lowered or "401" in lowered:
            return ApiKeyValidationResult(False, "API key was rejected by Gemini.")
        return ApiKeyValidationResult(
            False,
            f"Gemini could not verify this key. Check your connection and try again. ({detail[:120]})",
        )'''

replace_function(
    validator,
    "def _validate_with_gemini(",
    "\ndef validate_gemini_api_key(",
    validator_function,
)
print("Changed key verification to probe a real Gemini Live WebSocket session.")

live_model = Path("/app/core/live_model.py")
source = live_model.read_text(encoding="utf-8")
old = '''    if not live_models:
        raise RuntimeError(
            "No Gemini Live-capable model is available for this API key. "
            "Check that Gemini Live API access is enabled."
        )'''
new = '''    if not live_models:
        # Some projects/keys do not expose Live capability in models.list().
        # Fall back to the configured model; the subsequent Live WebSocket
        # handshake is the authoritative permission check.
        print(
            "[JARVIS] Gemini models.list() did not expose Live capability metadata; "
            f"attempting configured live_model={configured} directly."
        )
        return configured'''
if source.count(old) != 1:
    raise RuntimeError("Could not find the expected Live model metadata gate.")
live_model.write_text(source.replace(old, new, 1), encoding="utf-8")
print("Removed the false-negative Live model-list gate; actual WebSocket access decides.")
