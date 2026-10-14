
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import quote, urlsplit

HOME = Path.home()
ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = Path(os.environ.get("VLADMIR_CONFIG", HOME / ".config/vladmir/config.json"))



DEFAULT_GENERAL_MODEL = "qwen3-vl:4b"
DEFAULT_ENGINEER_MODEL = "qwen2.5-coder:7b"

DEFAULTS = {
    "ollama": {"url": "http://127.0.0.1:11434", "model": DEFAULT_GENERAL_MODEL, "timeout": 180,
               "num_predict": 2048, "num_ctx": 8192, "temperature": 0.7,
               "top_p": 0.8, "top_k": 20, "repeat_penalty": 1.0, "keep_alive": 0},
    "models": {"chat": DEFAULT_GENERAL_MODEL, "call": DEFAULT_GENERAL_MODEL,
               "engineer": DEFAULT_ENGINEER_MODEL},
    "thinking": {"chat": False, "call": False},
    "camera": {"source": "auto", "device": "", "size": "1280x720", "fps": 10, "url": "", "scheme": "rtsps", "tls_verify": False, "timeout": 20},
    "audio": {
        "sample_rate": 16000, "frame_ms": 30, "threshold": 500,
        "min_speech_seconds": 0.18, "end_silence_seconds": 0.75,
        "max_utterance_seconds": 12, "calibration_seconds": 2,
        "source": "default", "sink": "",
    },
    "whisper": {
        "binary": "whisper-cli",
        "timeout": 90,
        "wake_model": str(HOME / ".local/share/vladmir/ggml-base.bin"),
        "command_model": str(HOME / ".local/share/vladmir/ggml-small.bin"),
    },
    "tts": {
        "python": str(HOME / ".local/share/vladmir/piper-env/bin/python"),
        "voice_pt": str(HOME / ".local/share/vladmir/voices/pt_BR-faber-medium.onnx"),
        "voice_en": str(HOME / ".local/share/vladmir/voices/en_US-lessac-medium.onnx"),
        "synth_timeout": 60, "playback_timeout": 180, "fallback_timeout": 60,
    },
    "cognition": {"enabled": True, "model_provider": "ollama", "telemetry": False,
                  "knowledge_db": str(HOME / ".local/state/vladmir/cognition/knowledge.sqlite3")},

    "free_ai": {"enabled": False, "mode": "explicit", "timeout": 15,
                "max_attempts": 2, "daily_per_endpoint": 10},

    "honcho": {"enabled": False, "share_conversations": False,
               "base_url": "https://api.honcho.dev", "workspace_id": "vladmir",
               "owner_peer_id": "owner", "assistant_peer_id": "vladmir",
               "session_id": "shared", "timeout_seconds": 4},

    "sentinel": {"share_hash_with_virustotal": False, "virustotal_api_key": ""},
    "web": {"enabled": True, "timeout": 5}, "plugins": {}, "memory": {"max_messages": 6},
    "paths": {"tmp": str(ROOT / "tmp"), "logs": str(ROOT / "logs")},
}


def load_config() -> dict:

    cfg = json.loads(json.dumps(DEFAULTS))
    if CONFIG_FILE.is_file():
        with CONFIG_FILE.open(encoding="utf-8") as f:
            local = json.load(f)
        for section, values in local.items():
            if isinstance(values, dict) and section in cfg:
                cfg[section].update(values)
    if os.getenv("VLADMIR_KNOWLEDGE_DB"):
        cfg["cognition"]["knowledge_db"] = os.environ["VLADMIR_KNOWLEDGE_DB"]
    if os.getenv("VLADMIR_CAMERA_URL"):
        cfg["camera"]["url"] = os.environ["VLADMIR_CAMERA_URL"]
    if os.getenv("VLADMIR_OLLAMA_URL"):
        cfg["ollama"]["url"] = os.environ["VLADMIR_OLLAMA_URL"]
    if os.getenv("VLADMIR_WEB"):
        cfg["web"]["enabled"] = os.environ["VLADMIR_WEB"].lower() not in {"0", "false", "no"}
    if os.getenv("VLADMIR_AUDIO_SOURCE"):
        cfg["audio"]["source"] = os.environ["VLADMIR_AUDIO_SOURCE"]
    if os.getenv("VLADMIR_AUDIO_SINK"):
        cfg["audio"]["sink"] = os.environ["VLADMIR_AUDIO_SINK"]
    if os.getenv("VLADMIR_VT_API_KEY"):
        cfg["sentinel"]["virustotal_api_key"] = os.environ["VLADMIR_VT_API_KEY"]
    validate_model_profiles(cfg)
    return cfg


def validate_model_profiles(cfg: dict) -> None:

    models = cfg.get("models")
    fallback = cfg.get("ollama", {}).get("model")
    if not isinstance(models, dict) or not models or not isinstance(fallback, str) or not fallback.strip():
        raise ValueError("Configure ao menos um perfil de modelo local para o Vladmir.")
    names = [fallback, *models.values()]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("Os nomes dos perfis de modelo precisam ser textos não vazios.")


def camera_url(cfg: dict) -> str:

    cam = cfg["camera"]
    if cam.get("url"):
        url = str(cam["url"])
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError:
            raise ValueError("A URL da câmera tem uma porta inválida; use uma porta entre 1 e 65535.") from None
        if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.hostname:
            raise ValueError("A URL da câmera deve usar RTSP/RTSPS e informar um host válido.")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("A porta RTSP/RTSPS da câmera deve ser um número entre 1 e 65535.")
        return url
    host = cam.get("host", "")
    if not host:
        return ""
    scheme = str(cam.get("scheme", "rtsps")).lower()
    if scheme not in {"rtsp", "rtsps"}:
        raise ValueError("O protocolo da câmera deve ser RTSP ou RTSPS.")
    user = quote(str(cam.get("username", "")), safe="")
    password = quote(str(cam.get("password", "")), safe="")
    auth = f"{user}:{password}@" if user or password else ""
    default_port = 554 if scheme == "rtsp" else 8554
    try:
        port = int(cam.get("port", default_port))
    except (TypeError, ValueError):
        raise ValueError("A porta RTSP/RTSPS da câmera deve ser um número entre 1 e 65535.") from None
    if not 1 <= port <= 65535:
        raise ValueError("A porta RTSP/RTSPS da câmera deve ser um número entre 1 e 65535.")
    path = str(cam.get("path", "/live"))
    if not path.startswith("/"):
        path = "/" + path
    return f"{scheme}://{auth}{host}:{port}{path}"
