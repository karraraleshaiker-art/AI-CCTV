from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .alerts import AlertStore
from .config import AppConfig, mask_camera_source, resolve_camera_source
from .detections import Detection
from .detector import DetectorError, YoloDetector, split_detections
from .state import RuntimeState
from .tracker import PersonTracker, Track
from .zones import Zone


@dataclass(slots=True)
class PipelineSnapshot:
    running: bool
    frame_count: int
    fps: float
    tracks: list[dict[str, Any]]
    alerts: list[dict[str, object]]
    error: str | None
    status: str


@dataclass(frozen=True, slots=True)
class PendingAlert:
    kind: str
    track_id: int
    message: str


class CCTVPipeline:
    def __init__(self, config: AppConfig, state: RuntimeState) -> None:
        self.config = config
        self.state = state
        self.alerts = AlertStore(
            config.alert_cooldown_seconds,
            history_path=config.alert_history_path,
            max_events=config.alert_history_limit,
        )
        self.tracker = PersonTracker()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest_jpeg: bytes | None = None
        self._frame_count = 0
        self._fps = 0.0
        self._error: str | None = None
        self._status = "Starting"
        self._tracks_payload: list[dict[str, Any]] = []

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="cctv-pipeline", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def latest_jpeg(self) -> bytes | None:
        with self._lock:
            return self._latest_jpeg

    def placeholder_jpeg(self) -> bytes:
        with self._lock:
            status = self._status
            error = self._error
        return make_status_frame(status, error)

    def snapshot(self) -> PipelineSnapshot:
        with self._lock:
            return PipelineSnapshot(
                running=bool(self._thread and self._thread.is_alive()),
                frame_count=self._frame_count,
                fps=self._fps,
                tracks=list(self._tracks_payload),
                alerts=self.alerts.recent(),
                error=self._error,
                status=self._status,
            )

    def _run(self) -> None:
        capture = None
        try:
            self._set_status("Loading AI model")
            detector = YoloDetector(
                self.config.model_name,
                confidence=self.config.confidence,
                iou_threshold=self.config.iou_threshold,
            )
            self._set_status("Connecting to camera")
            camera_source = resolve_camera_source(self.config)
            capture = open_video_capture(camera_source, self.config.rtsp_capture_options)
            if not capture.isOpened():
                raise RuntimeError(f"Could not open camera source: {mask_camera_source(str(camera_source))}")

            self._set_status("Waiting for frames")
            last_tick = time.monotonic()
            frames_since_tick = 0
            failed_reads = 0
            target_delay = 1.0 / max(1, self.config.stream_fps)

            while not self._stop.is_set():
                loop_started = time.monotonic()
                drop_stale_frames(capture, self.config.rtsp_stale_frame_grabs)
                ok, frame = capture.read()
                if not ok:
                    failed_reads += 1
                    if failed_reads % max(1, self.config.failed_read_reconnect_frames) == 0:
                        self._set_error(
                            "Connected to camera, but no frames are arriving. Check RTSP stream, channel, "
                            "main/substream setting, and whether another app is already using the stream."
                        )
                        capture.release()
                        if self._stop.wait(self.config.camera_reconnect_seconds):
                            break
                        self._set_status("Reconnecting to camera")
                        capture = open_video_capture(camera_source, self.config.rtsp_capture_options)
                        failed_reads = 0
                    time.sleep(0.2)
                    continue

                failed_reads = 0
                frame = resize_frame(frame, self.config.frame_width)
                detections = detector.detect(frame)
                people, phones = split_detections(detections)
                tracks = self.tracker.update(people)
                zone = self.state.zone.to_pixels(frame.shape[1], frame.shape[0])
                pending_alerts = self._evaluate_tracks(tracks, phones, zone)
                annotated = self._draw(frame, tracks, phones, zone)
                self._save_alerts(pending_alerts, annotated)
                ok, encoded = cv2.imencode(
                    ".jpg",
                    annotated,
                    [int(cv2.IMWRITE_JPEG_QUALITY), normalized_jpeg_quality(self.config.jpeg_quality)],
                )
                if ok:
                    with self._lock:
                        self._latest_jpeg = encoded.tobytes()
                        self._frame_count += 1
                        self._tracks_payload = [track_payload(track, zone) for track in tracks]
                        self._error = None
                        self._status = "Processing live camera"

                frames_since_tick += 1
                now = time.monotonic()
                elapsed = now - last_tick
                if elapsed >= 1.0:
                    with self._lock:
                        self._fps = frames_since_tick / elapsed
                    frames_since_tick = 0
                    last_tick = now

                sleep_for = target_delay - (time.monotonic() - loop_started)
                if sleep_for > 0:
                    time.sleep(sleep_for)
        except (DetectorError, Exception) as exc:
            self._set_error(str(exc))
        finally:
            if capture is not None:
                capture.release()

    def _set_status(self, status: str) -> None:
        with self._lock:
            self._status = status

    def _set_error(self, error: str) -> None:
        with self._lock:
            self._error = error
            self._status = "Camera error"

    def _evaluate_tracks(self, tracks: list[Track], phones: list[Detection], zone: Zone) -> list[PendingAlert]:
        pending_alerts: list[PendingAlert] = []
        for track in tracks:
            foot_point = ((track.bbox.x1 + track.bbox.x2) / 2.0, track.bbox.y2)
            inside_zone = zone.contains(foot_point)
            if inside_zone:
                track.inside_zone_frames += 1
                track.outside_zone_frames = 0
                if track.inside_zone_frames >= 3:
                    track.was_confirmed_inside_zone = True
            else:
                track.outside_zone_frames += 1

            if track.was_confirmed_inside_zone and track.outside_zone_frames == self.config.leave_persistence_frames:
                pending_alerts.append(
                    PendingAlert(
                        kind="left_zone",
                        track_id=track.id,
                        message=f"Person #{track.id} left the assigned place.",
                    )
                )

            phone_near = any(is_phone_near_person(phone, track) for phone in phones)
            if phone_near:
                track.phone_frames += 1
            else:
                track.phone_frames = 0

            if track.phone_frames == self.config.phone_persistence_frames:
                pending_alerts.append(
                    PendingAlert(
                        kind="phone_use",
                        track_id=track.id,
                        message=f"Person #{track.id} appears to be using a phone.",
                    )
                )
        return pending_alerts

    def _save_alerts(self, pending_alerts: list[PendingAlert], frame) -> None:
        for pending in pending_alerts:
            evidence_path = self._save_evidence_frame(pending, frame)
            self.alerts.add(
                kind=pending.kind,
                track_id=pending.track_id,
                message=pending.message,
                evidence_path=evidence_path,
            )

    def _save_evidence_frame(self, alert: PendingAlert, frame) -> Path | None:
        evidence_dir = Path(self.config.evidence_dir)
        try:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{time.strftime('%Y%m%d_%H%M%S')}_{alert.kind}_track_{alert.track_id}_{time.time_ns()}.jpg"
            path = evidence_dir / filename
            if cv2.imwrite(str(path), frame):
                return path
        except OSError:
            return None
        return None

    def _draw(self, frame, tracks: list[Track], phones: list[Detection], zone: Zone):
        draw_zone(frame, zone)
        for phone in phones:
            x1, y1, x2, y2 = phone.bbox.as_int_tuple()
            cv2.rectangle(frame, (x1, y1), (x2, y2), (60, 180, 255), 2)
            cv2.putText(frame, "phone", (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 180, 255), 2)

        for track in tracks:
            x1, y1, x2, y2 = track.bbox.as_int_tuple()
            foot_point = (int((track.bbox.x1 + track.bbox.x2) / 2.0), int(track.bbox.y2))
            inside = zone.contains(foot_point)
            color = (50, 220, 90) if inside else (45, 80, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame, foot_point, 4, color, -1)
            label = f"person #{track.id}"
            if track.phone_frames >= self.config.phone_persistence_frames:
                label += " PHONE"
            elif track.was_confirmed_inside_zone and track.outside_zone_frames >= self.config.leave_persistence_frames:
                label += " LEFT"
            cv2.putText(frame, label, (x1, max(18, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        return frame


def resize_frame(frame, target_width: int):
    if target_width <= 0 or frame.shape[1] <= target_width:
        return frame
    ratio = target_width / frame.shape[1]
    height = int(frame.shape[0] * ratio)
    return cv2.resize(frame, (target_width, height), interpolation=cv2.INTER_AREA)


def open_video_capture(source: int | str, rtsp_capture_options: str | None = None):
    if isinstance(source, str) and source.lower().startswith("rtsp://"):
        environ.setdefault(
            "OPENCV_FFMPEG_CAPTURE_OPTIONS",
            rtsp_capture_options or "rtsp_transport;tcp|max_delay;500000",
        )
    capture = cv2.VideoCapture()
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 8000)
    capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 8000)
    if isinstance(source, str) and source.lower().startswith("rtsp://"):
        capture.open(source, cv2.CAP_FFMPEG)
    else:
        capture.open(source)
    return capture


def drop_stale_frames(capture, stale_frame_grabs: int) -> None:
    for _ in range(max(0, stale_frame_grabs)):
        if not capture.grab():
            break


def normalized_jpeg_quality(value: int) -> int:
    return min(95, max(35, int(value)))


def make_status_frame(status: str, error: str | None) -> bytes:
    frame = np.zeros((540, 960, 3), dtype=np.uint8)
    frame[:, :] = (17, 20, 23)
    cv2.putText(frame, "AI CCTV Monitor", (44, 82), cv2.FONT_HERSHEY_SIMPLEX, 1.05, (238, 243, 244), 2)
    cv2.putText(frame, status or "Starting", (44, 142), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (243, 201, 79), 2)

    lines = wrap_text(error or "Waiting for the first camera frame...", 72)
    y = 214
    for line in lines[:8]:
        cv2.putText(frame, line, (44, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (174, 186, 193), 1)
        y += 34

    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        return b""
    return encoded.tobytes()


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def is_phone_near_person(phone: Detection, track: Track) -> bool:
    upper = track.bbox.upper_region().expanded(0.08)
    phone_center = phone.bbox.center
    if upper.contains_point(phone_center):
        return True
    return phone.bbox.distance_to(upper) <= max(35.0, track.bbox.width * 0.18)


def draw_zone(frame, zone: Zone) -> None:
    if len(zone.points) < 3:
        return
    points = [(int(x), int(y)) for x, y in zone.points]
    for index, point in enumerate(points):
        nxt = points[(index + 1) % len(points)]
        cv2.line(frame, point, nxt, (255, 200, 60), 2)
        cv2.circle(frame, point, 4, (255, 200, 60), -1)
    cv2.putText(frame, "assigned place", points[0], cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 60), 2)


def track_payload(track: Track, zone: Zone) -> dict[str, Any]:
    foot_point = ((track.bbox.x1 + track.bbox.x2) / 2.0, track.bbox.y2)
    return {
        "id": track.id,
        "bbox": track.bbox.as_int_tuple(),
        "inside_zone": zone.contains(foot_point),
        "confirmed_inside_zone": track.was_confirmed_inside_zone,
        "phone_frames": track.phone_frames,
        "outside_zone_frames": track.outside_zone_frames,
    }
