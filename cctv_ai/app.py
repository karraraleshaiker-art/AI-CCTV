from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import AppConfig, display_camera_source, mask_camera_source
from .pipeline import CCTVPipeline
from .state import RuntimeState


class ZoneRequest(BaseModel):
    points: list[tuple[float, float]] = Field(min_length=3)


def create_app(config: AppConfig) -> FastAPI:
    state = RuntimeState(config.state_path, config.initial_zone)
    pipeline = CCTVPipeline(config, state)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        pipeline.start()
        yield
        pipeline.stop()

    app = FastAPI(title="AI CCTV Monitor", lifespan=lifespan)
    static_dir = Path(__file__).resolve().parent.parent / "static"
    evidence_dir = Path(config.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/evidence", StaticFiles(directory=evidence_dir), name="evidence")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return (static_dir / "index.html").read_text(encoding="utf-8")

    @app.get("/video")
    async def video() -> StreamingResponse:
        return StreamingResponse(stream_frames(pipeline), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/status")
    async def status() -> dict[str, object]:
        snapshot = pipeline.snapshot()
        return {
            "running": snapshot.running,
            "frame_count": snapshot.frame_count,
            "fps": round(snapshot.fps, 2),
            "tracks": snapshot.tracks,
            "alerts": with_evidence_urls(snapshot.alerts),
            "error": snapshot.error,
            "status": snapshot.status,
            "zone": state.zone.points,
            "config": {
                "camera_source": mask_camera_source(display_camera_source(config)),
                "input_mode": config.input_mode,
                "nvr_host": config.nvr_host,
                "nvr_port": config.nvr_port,
                "nvr_channel": config.nvr_channel,
                "nvr_stream": config.nvr_stream,
                "nvr_url_style": config.nvr_url_style,
                "model_name": config.model_name,
                "confidence": config.confidence,
                "model_imgsz": config.model_imgsz,
                "frame_width": config.frame_width,
                "stream_fps": config.stream_fps,
                "jpeg_quality": config.jpeg_quality,
            },
        }

    @app.post("/api/zone")
    async def set_zone(request: ZoneRequest) -> dict[str, object]:
        try:
            zone = state.set_zone(request.points)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"zone": zone.points}

    @app.get("/api/alerts")
    async def get_alerts(limit: int = 100) -> dict[str, object]:
        return {"alerts": with_evidence_urls(pipeline.alerts.recent(limit=limit))}

    @app.get("/api/logs", response_class=PlainTextResponse)
    async def get_logs(lines: int = 200, log: str = "app") -> str:
        log_name = "native_stderr.log" if log == "native" else "ai_cctv.log"
        log_path = Path(config.log_dir) / log_name
        if not log_path.exists():
            return "No runtime log file has been created yet."
        return tail_text(log_path, max_lines=min(max(lines, 1), 1000))

    @app.post("/api/alerts/{alert_id}/ack")
    async def acknowledge_alert(alert_id: str) -> dict[str, object]:
        if not pipeline.alerts.acknowledge(alert_id):
            raise HTTPException(status_code=404, detail="Alert not found.")
        return {"ok": True}

    return app


async def stream_frames(pipeline: CCTVPipeline):
    while True:
        frame = pipeline.latest_jpeg() or pipeline.placeholder_jpeg()
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        await asyncio.sleep(0.04)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AI CCTV monitor.")
    parser.add_argument("--config", default=None, help="Path to JSON config file.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    return parser.parse_args()


def with_evidence_urls(alerts: list[dict[str, object]]) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for alert in alerts:
        item = dict(alert)
        evidence_path = item.get("evidence_path")
        if evidence_path:
            item["evidence_url"] = f"/evidence/{Path(str(evidence_path)).name}"
        else:
            item["evidence_url"] = None
        payload.append(item)
    return payload


def tail_text(path: Path, max_lines: int) -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:])


def main() -> None:
    import uvicorn

    args = parse_args()
    config = AppConfig.from_file(args.config)
    from .logging_utils import configure_logging

    configure_logging(config.log_dir)
    app = create_app(config)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
