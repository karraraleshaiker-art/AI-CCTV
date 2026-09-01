from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit


Point = tuple[float, float]


@dataclass(slots=True)
class AppConfig:
    camera_source: str = ""
    input_mode: str = "nvr_rtsp"
    nvr_host: str = "192.168.100.203"
    nvr_port: int = 554
    nvr_username: str = "admin"
    nvr_password: str = ""
    nvr_channel: str = "14"
    nvr_stream: str = "main"
    nvr_url_style: str = "hikvision"
    nvr_path: str = ""
    model_name: str = "yolov8n.pt"
    confidence: float = 0.35
    iou_threshold: float = 0.45
    stream_fps: int = 10
    frame_width: int = 640
    jpeg_quality: int = 70
    rtsp_stale_frame_grabs: int = 2
    rtsp_capture_options: str = "rtsp_transport;tcp|max_delay;500000"
    phone_persistence_frames: int = 5
    leave_persistence_frames: int = 8
    alert_cooldown_seconds: float = 10.0
    alert_history_path: str = "output/alerts/alerts.jsonl"
    alert_history_limit: int = 200
    evidence_dir: str = "output/evidence"
    failed_read_reconnect_frames: int = 25
    camera_reconnect_seconds: float = 5.0
    state_path: str = "runtime_state.json"
    initial_zone: list[Point] = field(
        default_factory=lambda: [(0.2, 0.2), (0.8, 0.2), (0.8, 0.85), (0.2, 0.85)]
    )

    @classmethod
    def from_file(cls, path: str | Path | None) -> "AppConfig":
        if path is None:
            return cls()

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        data = json.loads(config_path.read_text(encoding="utf-8"))
        return cls.from_mapping(data)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "AppConfig":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        clean = {key: value for key, value in data.items() if key in allowed}
        if "initial_zone" in clean:
            clean["initial_zone"] = [tuple(point) for point in clean["initial_zone"]]
        return cls(**clean)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_camera_source(source: str) -> int | str:
    stripped = source.strip()
    if stripped.isdigit():
        return int(stripped)
    return stripped


def resolve_camera_source(config: AppConfig) -> int | str:
    if config.camera_source.strip():
        return parse_camera_source(config.camera_source)
    if config.input_mode != "nvr_rtsp":
        raise ValueError(f"Unsupported input_mode: {config.input_mode}")
    return build_rtsp_url(
        host=config.nvr_host,
        port=config.nvr_port,
        username=config.nvr_username,
        password=config.nvr_password,
        channel=config.nvr_channel,
        stream=config.nvr_stream,
        url_style=config.nvr_url_style,
        path=config.nvr_path,
    )


def display_camera_source(config: AppConfig) -> str:
    source = resolve_camera_source(config)
    return str(source)


def mask_camera_source(source: str) -> str:
    if "://" not in source or "@" not in source:
        return source
    parts = urlsplit(source)
    if not parts.username:
        return source
    host = parts.hostname or ""
    port = f":{parts.port}" if parts.port else ""
    netloc = f"{parts.username}:****@{host}{port}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def build_rtsp_url(
    host: str,
    port: int,
    username: str,
    password: str,
    channel: str,
    stream: str,
    url_style: str,
    path: str = "",
) -> str:
    user = quote(username, safe="")
    secret = quote(password, safe="")
    rtsp_path = normalize_rtsp_path(path) if path else build_rtsp_path(channel, stream, url_style)
    return f"rtsp://{user}:{secret}@{host}:{port}{rtsp_path}"


def build_rtsp_path(channel: str, stream: str, url_style: str) -> str:
    normalized_stream = stream.strip().lower()
    if normalized_stream not in {"main", "sub"}:
        raise ValueError("nvr_stream must be 'main' or 'sub'.")

    if url_style == "hikvision":
        stream_code = "01" if normalized_stream == "main" else "02"
        return f"/Streaming/Channels/{channel}{stream_code}"
    if url_style == "dahua":
        subtype = "0" if normalized_stream == "main" else "1"
        return f"/cam/realmonitor?channel={channel}&subtype={subtype}"
    if url_style == "generic":
        stream_name = "0.1" if normalized_stream == "main" else "0.2"
        if channel in {"", "1"}:
            return f"/{stream_name}"
        return f"/channel{channel}/{stream_name}"
    raise ValueError("nvr_url_style must be 'hikvision', 'dahua', or 'generic'.")


def normalize_rtsp_path(path: str) -> str:
    stripped = path.strip()
    return stripped if stripped.startswith("/") else f"/{stripped}"
