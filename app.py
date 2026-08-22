#!/usr/bin/env bash
"""
AI-CCTV — Intelligent Production & Compliance Monitoring Platform
Specialized for Solar Panel Manufacturing Facility (Al Noor Factory)
FastAPI Web Application with Multi-Stream Video Ingestion, Real-Time YOLO11 Inference,
Interactive Zone Drawing, Temporal Rules Engine & Supervisor Human-in-the-Loop Review.
"""
import asyncio
import base64
import getpass
import json
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote

import cv2
import numpy as np
import psutil
import torch
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from ultralytics import YOLO

# ---------------------------------------------------------------------------
# Global Constants & Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
SETTINGS_FILE = ROOT / "settings.json"
STATIC_DIR = ROOT / "static"
STATIC_DIR.mkdir(exist_ok=True)

PERSON_CLASS = 0
PHONE_CLASS = 67

# Solar Factory Color Palette
COLOR_GREEN = (0, 220, 0)
COLOR_RED = (0, 0, 255)
COLOR_WHITE = (255, 255, 255)
COLOR_CYAN = (212, 182, 6)     # BGR for Solar Cyan
COLOR_AMBER = (11, 158, 245)    # BGR for Warning Amber
COLOR_PURPLE = (246, 92, 139)   # BGR for Restricted Zone

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[CONFIG] Error loading settings.json: {e}")
    return {
        "nvr_ip": "192.168.100.203",
        "rtsp_port": 554,
        "nvr_user": "admin",
        "nvr_pass": "",
        "model": "yolo11s.pt",
        "device": "auto",
        "imgsz": 640,
        "person_conf": 0.35,
        "phone_conf": 0.30,
        "iou": 0.45,
        "max_ai_fps": 10.0,
        "display_max_width": 1600,
        "tracker": "bytetrack.yaml",
        "absence_threshold_sec": 120,
        "phone_duration_sec": 5,
        "active_cameras": [14, 15],
        "default_stream": "01",
        "zones": {}
    }

def save_settings(s: dict):
    SETTINGS_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")

SETTINGS = load_settings()

# Auto-detect best PyTorch device
def get_best_device() -> str:
    cfg = SETTINGS.get("device", "auto")
    if cfg != "auto":
        return cfg
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"

ACTIVE_DEVICE = get_best_device()
print(f"[SYSTEM] Hardware Acceleration Device Selected: {ACTIVE_DEVICE.upper()}")

from database import (
    init_db,
    db_save_incident,
    db_get_incidents,
    db_update_incident_review,
    db_get_zones_for_cam,
    db_save_zones_for_cam,
    db_get_employees,
    db_save_employee,
    db_delete_employee,
    db_load_all_face_embeddings,
)
from face_engine import GLOBAL_FACE_ENGINE

# ---------------------------------------------------------------------------
# Incident & Rules Management
# ---------------------------------------------------------------------------
class Incident:
    def __init__(self, incident_id: str, cam_id: int, event_type: str, severity: str, title: str, details: str, snapshot_b64: str = ""):
        self.id = incident_id
        self.cam_id = cam_id
        self.event_type = event_type  # absence, phone, restricted, offline
        self.severity = severity      # high, medium, low
        self.title = title
        self.details = details
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_epoch = time.time()
        self.status = "pending"       # pending, verified, dismissed
        self.snapshot_b64 = snapshot_b64

    def to_dict(self):
        return {
            "id": self.id,
            "cam_id": self.cam_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "title": self.title,
            "details": self.details,
            "timestamp": self.timestamp,
            "timestamp_epoch": self.timestamp_epoch,
            "status": self.status,
            "snapshot_b64": self.snapshot_b64
        }

INCIDENTS_LOCK = threading.Lock()
INCIDENTS: List[Incident] = []

def add_incident(incident: Incident):
    with INCIDENTS_LOCK:
        # Avoid duplicate alerts of same type on same camera within 15 seconds
        for inc in reversed(INCIDENTS[-10:]):
            if inc.cam_id == incident.cam_id and inc.event_type == incident.event_type and (time.time() - inc.timestamp_epoch < 15):
                return
        INCIDENTS.append(incident)
        if len(INCIDENTS) > 100:
            INCIDENTS.pop(0)

    # Persist into SQLite asynchronously
    def _save_bg():
        try:
            asyncio.run(db_save_incident(incident.to_dict()))
        except Exception as err:
            print(f"[DB ERROR] Saving incident: {err}")

    threading.Thread(target=_save_bg, daemon=True).start()

# ---------------------------------------------------------------------------
# Camera RTSP Stream Worker
# ---------------------------------------------------------------------------
class CameraStream:
    def __init__(self, cam_id: int, suffix: str = "01"):
        self.cam_id = cam_id
        self.suffix = suffix
        self.lock = threading.Lock()
        self.frame: Optional[np.ndarray] = None
        self.annotated_frame: Optional[np.ndarray] = None
        self.seq = 0
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.status = "INIT"
        self.fps = 0.0
        self.last_frame_time = 0.0
        self.width = 1280
        self.height = 720

    def get_rtsp_url(self) -> str:
        user = SETTINGS.get("nvr_user", "admin")
        pwd = SETTINGS.get("nvr_pass", "")
        ip = SETTINGS.get("nvr_ip", "192.168.100.203")
        port = SETTINGS.get("rtsp_port", 554)
        if user and pwd:
            auth = f"{quote(user, safe='')}:{quote(pwd, safe='')}@"
        elif user:
            auth = f"{quote(user, safe='')}@"
        else:
            auth = ""
        return f"rtsp://{auth}{ip}:{port}/Streaming/channels/{self.cam_id}{self.suffix}"

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _open_capture(self):
        url = self.get_rtsp_url()
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;4000000"
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        return cap

    def _generate_synthetic_frame(self, frame_num: int) -> np.ndarray:
        """Generates a high-tech synthetic feed when actual RTSP is offline or during testing."""
        h, w = 720, 1280
        img = np.zeros((h, w, 3), dtype=np.uint8)
        # Background gradient & grid
        for y in range(0, h, 40):
            cv2.line(img, (0, y), (w, y), (20, 26, 38), 1)
        for x in range(0, w, 40):
            cv2.line(img, (x, 0), (x, h), (20, 26, 38), 1)

        # Simulation moving box
        t = time.time()
        cx = int(w/2 + 200 * np.sin(t * 0.8))
        cy = int(h/2 + 100 * np.cos(t * 0.8))
        
        # Draw mock person silhouette box
        cv2.rectangle(img, (cx-40, cy-90), (cx+40, cy+90), (45, 55, 75), -1)
        cv2.rectangle(img, (cx-40, cy-90), (cx+40, cy+90), (80, 120, 160), 2)
        cv2.putText(img, "WORKER SIMULATION", (cx-55, cy-98), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 180, 220), 1)

        # Status Overlay
        cv2.rectangle(img, (20, 20), (520, 110), (12, 18, 28), -1)
        cv2.rectangle(img, (20, 20), (520, 110), (59, 130, 246), 1)
        cv2.putText(img, f"AL NOOR SOLAR FACTORY — CAM D{self.cam_id}", (35, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (240, 240, 240), 2)
        cv2.putText(img, f"RTSP: {self.get_rtsp_url()}", (35, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 160, 180), 1)
        cv2.putText(img, f"STATUS: {self.status} (RETRYING NVR ON {SETTINGS.get('nvr_ip')})", (35, 96),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (6, 182, 212), 1)
        return img

    def _capture_loop(self):
        fps_count = 0
        fps_t = time.time()
        synthetic_mode = False

        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self.status = "CONNECTING"
                try:
                    self.cap = self._open_capture()
                except Exception as e:
                    self.cap = None

                if self.cap is None or not self.cap.isOpened():
                    self.status = "OFFLINE / SIMULATING"
                    synthetic_mode = True
                    time.sleep(0.5)

            if synthetic_mode:
                f = self._generate_synthetic_frame(self.seq)
                time.sleep(0.04)  # ~25 fps
                with self.lock:
                    self.frame = f
                    self.seq += 1
                    self.height, self.width = f.shape[:2]
                # Periodically attempt real connection
                if self.seq % 150 == 0:
                    synthetic_mode = False
                    if self.cap:
                        self.cap.release()
                    self.cap = None
                continue

            ok, f = self.cap.read()
            if not ok or f is None:
                self.status = "RECONNECTING"
                if self.cap:
                    self.cap.release()
                self.cap = None
                synthetic_mode = True
                time.sleep(0.2)
                continue

            self.status = "LIVE"
            synthetic_mode = False
            with self.lock:
                self.frame = f
                self.seq += 1
                self.height, self.width = f.shape[:2]

            fps_count += 1
            dt = time.time() - fps_t
            if dt >= 1.0:
                self.fps = fps_count / dt
                fps_count = 0
                fps_t = time.time()

    def get_latest(self):
        with self.lock:
            return (None, self.seq) if self.frame is None else (self.frame.copy(), self.seq)

    def set_annotated(self, ann_frame: np.ndarray):
        with self.lock:
            self.annotated_frame = ann_frame

    def get_annotated_jpeg(self) -> bytes:
        with self.lock:
            frame = self.annotated_frame if self.annotated_frame is not None else self.frame
        if frame is None:
            frame = self._generate_synthetic_frame(0)
        
        # Resize for smooth streaming if larger than max width
        max_w = SETTINGS.get("display_max_width", 1280)
        if frame.shape[1] > max_w:
            sc = max_w / frame.shape[1]
            frame = cv2.resize(frame, (int(frame.shape[1] * sc), int(frame.shape[0] * sc)), interpolation=cv2.INTER_AREA)

        ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return buffer.tobytes() if ret else b""

    def stop(self):
        self.running = False
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.5)

# ---------------------------------------------------------------------------
# Multi-Camera AI Pipeline & Rules Engine
# ---------------------------------------------------------------------------
class MultiCameraAIProcessor:
    def __init__(self):
        self.streams: Dict[int, CameraStream] = {}
        self.model: Optional[YOLO] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.ai_fps = 0.0
        self.ai_ms = 0.0
        self.lock = threading.Lock()
        
        # Biometric Face Roster: list of (id, name, code, assigned_zone, np_embedding)
        self.face_roster: list = []
        # Keyframe Track Identity Cache: { (cam_id, track_id): (full_name, emp_code, assigned_zone, score) }
        self.track_identity_cache: Dict[Tuple[int, int], Tuple[str, str, Optional[str], float]] = {}

        # Zone absence tracking state: { (cam_id, zone_id): last_seen_epoch }
        self.zone_last_seen: Dict[tuple, float] = {}
        # Phone duration tracking: { (cam_id, track_id): first_detected_epoch }
        self.phone_tracking: Dict[tuple, float] = {}

    def reload_face_roster(self):
        """Asynchronously loads all active employee face embeddings into active memory."""
        def _load():
            try:
                roster = asyncio.run(db_load_all_face_embeddings())
                with self.lock:
                    self.face_roster = roster
                    self.track_identity_cache.clear()
                print(f"[BIOMETRIC] Loaded {len(roster)} employee face embedding(s) into active memory.")
            except Exception as e:
                print(f"[BIOMETRIC] Error loading face roster: {e}")
        threading.Thread(target=_load, daemon=True).start()

    def start(self):
        # Load registered face embeddings
        self.reload_face_roster()

        # Initialize camera streams based on active_cameras setting
        active_cams = SETTINGS.get("active_cameras", [14, 15])
        for cid in active_cams:
            stream = CameraStream(cid, SETTINGS.get("default_stream", "01"))
            stream.start()
            self.streams[cid] = stream

        self.running = True
        self.thread = threading.Thread(target=self._ai_loop, daemon=True)
        self.thread.start()

    def add_or_switch_camera(self, cam_id: int, suffix: str = "01"):
        with self.lock:
            if cam_id in self.streams:
                self.streams[cam_id].stop()
            stream = CameraStream(cam_id, suffix)
            stream.start()
            self.streams[cam_id] = stream
            # Update settings
            cams = list(self.streams.keys())
            SETTINGS["active_cameras"] = cams
            save_settings(SETTINGS)

    def remove_camera(self, cam_id: int):
        with self.lock:
            if cam_id in self.streams:
                self.streams[cam_id].stop()
                del self.streams[cam_id]
                SETTINGS["active_cameras"] = list(self.streams.keys())
                save_settings(SETTINGS)

    def _ai_loop(self):
        print(f"[AI MODEL] Loading {SETTINGS.get('model', 'yolo11s.pt')} on device '{ACTIVE_DEVICE}'...")
        try:
            self.model = YOLO(SETTINGS.get("model", "yolo11s.pt"))
            print("[AI MODEL] YOLO Model loaded successfully.")
        except Exception as e:
            print(f"[AI MODEL] Error loading YOLO: {e}")
            return

        last_run = 0.0
        fps_count = 0
        fps_t = time.time()

        while self.running:
            max_fps = max(1.0, float(SETTINGS.get("max_ai_fps", 10.0)))
            min_dt = 1.0 / max_fps
            if time.time() - last_run < min_dt:
                time.sleep(0.005)
                continue

            last_run = time.time()
            t0 = time.perf_counter()

            # Iterate over active cameras
            active_cams = list(self.streams.values())
            for stream in active_cams:
                frame, seq = stream.get_latest()
                if frame is None:
                    continue

                h, w = frame.shape[:2]
                dets = []

                # YOLO Tracking
                try:
                    conf_min = min(float(SETTINGS.get("person_conf", 0.35)), float(SETTINGS.get("phone_conf", 0.30)))
                    r = self.model.track(
                        frame,
                        persist=True,
                        tracker=SETTINGS.get("tracker", "bytetrack.yaml"),
                        imgsz=SETTINGS.get("imgsz", 640),
                        conf=conf_min,
                        iou=SETTINGS.get("iou", 0.45),
                        classes=[PERSON_CLASS, PHONE_CLASS],
                        verbose=False,
                        device=ACTIVE_DEVICE
                    )[0]

                    if r.boxes is not None and len(r.boxes):
                        boxes = r.boxes.xyxy.cpu().numpy()
                        cls = r.boxes.cls.cpu().numpy().astype(int)
                        conf = r.boxes.conf.cpu().numpy()
                        ids = r.boxes.id.cpu().numpy().astype(int) if r.boxes.id is not None else np.full(len(boxes), -1)

                        for b, c, cf, tid in zip(boxes, cls, conf, ids):
                            if c == PERSON_CLASS and cf >= SETTINGS.get("person_conf", 0.35):
                                dets.append(("person", b.tolist(), float(cf), int(tid)))
                            elif c == PHONE_CLASS and cf >= SETTINGS.get("phone_conf", 0.30):
                                dets.append(("phone", b.tolist(), float(cf), int(tid)))
                except Exception as e:
                    # Model inference fallback
                    pass

                # Apply Rules Engine, Face Biometrics & Render Overlays
                annotated = self._process_rules_and_render(stream.cam_id, frame, dets, w, h)
                stream.set_annotated(annotated)

            self.ai_ms = (time.perf_counter() - t0) * 1000.0
            fps_count += 1
            dt = time.time() - fps_t
            if dt >= 1.0:
                self.ai_fps = fps_count / dt
                fps_count = 0
                fps_t = time.time()

    def _process_rules_and_render(self, cam_id: int, frame: np.ndarray, dets: list, w: int, h: int) -> np.ndarray:
        out = frame.copy()
        zones = SETTINGS.get("zones", {}).get(str(cam_id), [])
        
        people_count = 0
        phone_count = 0
        person_feet_points = []
        person_phone_matched = False

        # 1. Draw Detections & Biometric Identity Fusion
        for typ, b, cf, tid in dets:
            x1, y1, x2, y2 = map(int, b)
            if typ == "person":
                people_count += 1
                feet = (int((x1 + x2) / 2), int(y2))
                person_feet_points.append((feet, tid))

                # Biometric Facial Recognition on Person Crop
                emp_name = None
                emp_code = None
                if tid >= 0 and self.face_roster:
                    if (cam_id, tid) in self.track_identity_cache:
                        emp_name, emp_code, _, _ = self.track_identity_cache[(cam_id, tid)]
                    else:
                        # Extract upper body crop for face recognition
                        pcrop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
                        if pcrop.size > 0 and pcrop.shape[0] > 50 and pcrop.shape[1] > 30:
                            m_name, m_code, m_zone, m_score = GLOBAL_FACE_ENGINE.detect_and_recognize_person_crop(
                                pcrop, self.face_roster, threshold=0.48
                            )
                            if m_name:
                                emp_name, emp_code = m_name, m_code
                                self.track_identity_cache[(cam_id, tid)] = (m_name, m_code, m_zone, m_score)

                if emp_name:
                    color = (255, 215, 0) # Cyan/Gold for identified employee
                    label = f"👤 {emp_name} ({emp_code}) | {cf:.2f}"
                else:
                    color = COLOR_GREEN
                    label = f"Worker {tid if tid >= 0 else ''} | {cf:.2f}"
            else:
                phone_count += 1
                color = COLOR_RED
                label = f"PHONE | {cf:.2f}"

            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            cv2.putText(out, label, (x1, max(20, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, color, 2)

        # 2. Evaluate Spatial Zones (Workstations & Restricted Areas)
        now = time.time()
        absence_threshold = float(SETTINGS.get("absence_threshold_sec", 120))
        phone_duration_thresh = float(SETTINGS.get("phone_duration_sec", 5))

        for zone in zones:
            z_id = zone.get("id", "z")
            z_name = zone.get("name", "Zone")
            z_type = zone.get("type", "workstation")
            poly_norm = zone.get("polygon", [])
            
            if len(poly_norm) >= 3:
                poly_pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in poly_norm], np.int32)
                
                # Check persons inside polygon
                workers_in_zone = 0
                for feet, tid in person_feet_points:
                    if cv2.pointPolygonTest(poly_pts, feet, False) >= 0:
                        workers_in_zone += 1

                # Workstation Absence Rule
                if z_type == "workstation":
                    key = (cam_id, z_id)
                    if workers_in_zone > 0:
                        self.zone_last_seen[key] = now
                        zone_color = (0, 200, 100) # Green / Safe
                        status_text = f"{z_name}: {workers_in_zone} Worker(s) Active"
                    else:
                        last_seen = self.zone_last_seen.get(key, now)
                        elapsed_absence = now - last_seen
                        if elapsed_absence > absence_threshold:
                            zone_color = COLOR_RED
                            status_text = f"⚠️ ABSENCE ALERT: {z_name} vacant for {int(elapsed_absence)}s"
                            # Trigger incident
                            add_incident(Incident(
                                incident_id=f"INC-{cam_id}-{int(now)}",
                                cam_id=cam_id,
                                event_type="absence",
                                severity="high",
                                title=f"Workstation Absence: {z_name}",
                                details=f"No operator detected at {z_name} for {int(elapsed_absence)} seconds."
                            ))
                        else:
                            zone_color = COLOR_AMBER
                            status_text = f"{z_name}: Vacant ({int(elapsed_absence)}s / {int(absence_threshold)}s)"

                # Restricted Zone Rule
                elif z_type == "restricted":
                    if workers_in_zone > 0:
                        zone_color = COLOR_RED
                        status_text = f"🚫 RESTRICTED BREACH: {workers_in_zone} person(s) inside {z_name}!"
                        add_incident(Incident(
                            incident_id=f"INC-BREACH-{cam_id}-{int(now)}",
                            cam_id=cam_id,
                            event_type="restricted",
                            severity="high",
                            title=f"Restricted Area Breach: {z_name}",
                            details=f"Unauthorized entry detected in {z_name}."
                        ))
                    else:
                        zone_color = COLOR_PURPLE
                        status_text = f"{z_name} (Secured)"

                # Draw semi-transparent polygon fill
                overlay = out.copy()
                cv2.fillPoly(overlay, [poly_pts], zone_color)
                cv2.addWeighted(overlay, 0.22, out, 0.78, 0, out)
                cv2.polylines(out, [poly_pts], isClosed=True, color=zone_color, thickness=2)
                
                # Label
                centroid = poly_pts.mean(axis=0).astype(int)
                cv2.putText(out, status_text, (max(10, centroid[0] - 100), max(30, centroid[1])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

        # 3. Phone Usage Duration Rule
        if phone_count > 0:
            key = (cam_id, "phone_active")
            first_seen = self.phone_tracking.get(key, now)
            self.phone_tracking[key] = first_seen
            phone_elapsed = now - first_seen
            if phone_elapsed >= phone_duration_thresh:
                add_incident(Incident(
                    incident_id=f"INC-PHONE-{cam_id}-{int(now)}",
                    cam_id=cam_id,
                    event_type="phone",
                    severity="high",
                    title="Active Phone Usage Violation",
                    details=f"Mobile phone operated continuously for {int(phone_elapsed)} seconds during production cycle."
                ))
        else:
            self.phone_tracking.pop((cam_id, "phone_active"), None)

        # 4. Top Telemetry Header
        cv2.rectangle(out, (0, 0), (w, 55), (10, 14, 23), -1)
        cv2.line(out, (0, 55), (w, 55), (59, 130, 246), 2)
        cv2.putText(out, f"AL NOOR SOLAR FACTORY | CAM D{cam_id}", (15, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        cv2.putText(out, f"Workers: {people_count}  |  Phones: {phone_count}  |  AI: {self.ai_fps:.1f} FPS ({self.ai_ms:.0f}ms) [{ACTIVE_DEVICE.upper()}]",
                    (15, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (6, 182, 212), 1)

        return out

    def stop(self):
        self.running = False
        for s in self.streams.values():
            s.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

AI_ENGINE = MultiCameraAIProcessor()

# ---------------------------------------------------------------------------
# FastAPI Application & Endpoints
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite Database & seed defaults
    try:
        await init_db(SETTINGS)
    except Exception as e:
        print(f"[DB INIT ERROR] {e}")
    AI_ENGINE.start()
    yield
    AI_ENGINE.stop()

app = FastAPI(
    title="AI-CCTV Solar Factory Monitoring Platform",
    description="Smart Video Analytics & Compliance Dashboard for Al Noor Solar Factory",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- Video Stream Endpoint (MJPEG) ---
@app.get("/api/stream/{cam_id}")
async def video_stream(cam_id: int):
    if cam_id not in AI_ENGINE.streams:
        # If camera not in active streams, try to add it
        AI_ENGINE.add_or_switch_camera(cam_id)

    stream = AI_ENGINE.streams.get(cam_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Camera stream not found")

    def frame_generator():
        while True:
            jpeg = stream.get_annotated_jpeg()
            if jpeg:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
            time.sleep(0.04)

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

# --- System Telemetry Endpoint ---
@app.get("/api/status")
def get_system_status():
    vm = psutil.virtual_memory()
    cams_info = []
    for cid, s in AI_ENGINE.streams.items():
        cams_info.append({
            "cam_id": cid,
            "status": s.status,
            "fps": round(s.fps, 1),
            "resolution": f"{s.width}x{s.height}",
            "suffix": s.suffix
        })

    with INCIDENTS_LOCK:
        total_inc = len(INCIDENTS)
        pending_inc = len([i for i in INCIDENTS if i.status == "pending"])

    return {
        "device": ACTIVE_DEVICE.upper(),
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": vm.percent,
        "ai_fps": round(AI_ENGINE.ai_fps, 1),
        "ai_ms": round(AI_ENGINE.ai_ms, 1),
        "cameras": cams_info,
        "total_incidents": total_inc,
        "pending_incidents": pending_inc
    }

# --- Settings & Cameras Management ---
class CameraSwitchReq(BaseModel):
    cam_id: int
    suffix: Optional[str] = "01"

@app.post("/api/cameras/switch")
def switch_camera(req: CameraSwitchReq):
    AI_ENGINE.add_or_switch_camera(req.cam_id, req.suffix or "01")
    return {"status": "ok", "active_cameras": list(AI_ENGINE.streams.keys())}

@app.post("/api/cameras/remove")
def remove_camera(req: CameraSwitchReq):
    AI_ENGINE.remove_camera(req.cam_id)
    return {"status": "ok", "active_cameras": list(AI_ENGINE.streams.keys())}

@app.get("/api/settings")
def get_settings():
    return SETTINGS

@app.post("/api/settings")
def update_settings(new_s: dict):
    global SETTINGS
    SETTINGS.update(new_s)
    save_settings(SETTINGS)
    return {"status": "ok", "settings": SETTINGS}

# --- Zones Management (SQLite Persistent) ---
class ZonePayload(BaseModel):
    cam_id: int
    zones: list

@app.get("/api/zones/{cam_id}")
async def get_zones(cam_id: int):
    try:
        zones = await db_get_zones_for_cam(cam_id)
        if zones:
            return zones
    except Exception as e:
        print(f"[DB GET ZONES] {e}")
    return SETTINGS.get("zones", {}).get(str(cam_id), [])

@app.post("/api/zones/{cam_id}")
async def save_zones(cam_id: int, payload: list):
    try:
        await db_save_zones_for_cam(cam_id, payload)
    except Exception as e:
        print(f"[DB SAVE ZONES] {e}")
    if "zones" not in SETTINGS:
        SETTINGS["zones"] = {}
    SETTINGS["zones"][str(cam_id)] = payload
    save_settings(SETTINGS)
    return {"status": "ok", "zones": payload}

# --- Incidents & Review (SQLite Persistent) ---
@app.get("/api/incidents")
async def get_incidents():
    try:
        db_incs = await db_get_incidents(limit=50)
        if db_incs:
            return db_incs
    except Exception as e:
        print(f"[DB GET INCIDENTS] {e}")
    with INCIDENTS_LOCK:
        return [i.to_dict() for i in reversed(INCIDENTS)]

class IncidentActionReq(BaseModel):
    action: str  # verified or dismissed
    reviewer: Optional[str] = "Supervisor"
    notes: Optional[str] = ""

@app.post("/api/incidents/{incident_id}/action")
async def review_incident(incident_id: str, req: IncidentActionReq):
    try:
        updated = await db_update_incident_review(
            incident_id=incident_id,
            action=req.action,
            reviewer=req.reviewer or "Supervisor",
            notes=req.notes or ""
        )
    except Exception as e:
        print(f"[DB REVIEW] {e}")
        updated = None

    with INCIDENTS_LOCK:
        for inc in INCIDENTS:
            if inc.id == incident_id:
                inc.status = req.action
                return {"status": "ok", "incident": inc.to_dict()}

# --- Employee Biometric & Directory Endpoints ---
class EmployeeEnrollReq(BaseModel):
    full_name: str
    employee_code: str
    department: Optional[str] = "Solar Assembly Line"
    assigned_zone_id: Optional[str] = None
    photo_base64: str

@app.get("/api/employees")
async def get_employees_list():
    try:
        return await db_get_employees()
    except Exception as e:
        print(f"[DB GET EMPLOYEES] {e}")
        return []

@app.post("/api/employees/enroll")
async def enroll_employee(req: EmployeeEnrollReq):
    try:
        raw_b64 = req.photo_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        img_bytes = base64.b64decode(raw_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image file format.")

        # Extract 128-D biometric embedding
        embedding = GLOBAL_FACE_ENGINE.extract_face_embedding(img)
        if embedding is None:
            raise HTTPException(
                status_code=400,
                detail="No clear human face detected in the photo. Please provide a clear, front-facing image."
            )

        emp_dir = STATIC_DIR / "employees"
        emp_dir.mkdir(exist_ok=True)
        photo_filename = f"emp_{req.employee_code.replace('/', '_')}_{int(time.time())}.jpg"
        photo_path = emp_dir / photo_filename
        cv2.imwrite(str(photo_path), img)

        emp = await db_save_employee(
            full_name=req.full_name,
            employee_code=req.employee_code,
            department=req.department or "Solar Assembly Line",
            assigned_zone_id=req.assigned_zone_id,
            face_embedding=embedding.tobytes(),
            photo_path=f"/static/employees/{photo_filename}"
        )

        # Refresh memory roster in AI Engine
        AI_ENGINE.reload_face_roster()
        return {"status": "ok", "employee": emp}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/employees/{emp_id}/delete")
async def delete_employee_profile(emp_id: int):
    ok = await db_delete_employee(emp_id)
    if ok:
        AI_ENGINE.reload_face_roster()
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Employee not found")

# ---------------------------------------------------------------------------
# High-Tech Web Dashboard UI (HTML / Tailwind CSS / Vanilla JS)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI-CCTV | Al Noor Factory for Solar Panels</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+Arabic:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #070a12;
            --bg-card: rgba(15, 23, 42, 0.8);
            --border: rgba(255, 255, 255, 0.08);
            --border-glow: rgba(6, 182, 212, 0.4);
            --cyan: #06b6d4;
            --blue: #3b82f6;
            --green: #10b981;
            --amber: #f59e0b;
            --red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Inter', 'Noto Sans Arabic', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-main);
            min-height: 100vh;
            background-image: 
                radial-gradient(circle at 10% 10%, rgba(6, 182, 212, 0.1) 0, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(59, 130, 246, 0.08) 0, transparent 40%);
            background-attachment: fixed;
        }

        /* Top Navbar */
        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.8rem 2rem;
            background: rgba(10, 14, 23, 0.85);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .brand-box {
            display: flex;
            align-items: center;
            gap: 1.2rem;
        }

        .brand-logo {
            height: 48px;
            width: auto;
            border-radius: 6px;
            filter: drop-shadow(0 2px 8px rgba(6, 182, 212, 0.3));
        }

        .brand-titles h1 {
            font-size: 1.25rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 40%, #7dd3fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-titles p {
            font-size: 0.78rem;
            color: var(--cyan);
            letter-spacing: 0.02em;
        }

        .nav-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 0.45rem 0.9rem;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .btn:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--cyan);
            transform: translateY(-1px);
        }

        .btn-cyan {
            background: linear-gradient(135deg, #0284c7, #0891b2);
            border-color: var(--cyan);
            box-shadow: 0 2px 10px rgba(6, 182, 212, 0.25);
        }

        /* Layout Grid */
        .main-container {
            max-width: 1720px;
            margin: 0 auto;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        /* Stats Strip */
        .stats-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }

        .stat-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1rem 1.25rem;
            backdrop-filter: blur(12px);
        }

        .stat-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
        }

        .stat-val {
            font-size: 1.6rem;
            font-weight: 800;
            margin-top: 0.2rem;
            color: #fff;
            display: flex;
            align-items: baseline;
            gap: 0.4rem;
        }

        /* Video Workspace */
        .workspace-grid {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 1.5rem;
        }

        @media (max-width: 1200px) {
            .workspace-grid { grid-template-columns: 1fr; }
        }

        .cameras-section {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-card);
            padding: 0.75rem 1.25rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }

        .camera-views-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 1.25rem;
        }

        .cam-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            position: relative;
        }

        .cam-card:hover {
            border-color: var(--border-glow);
        }

        .cam-card-header {
            padding: 0.6rem 1rem;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
        }

        .cam-title {
            font-size: 0.92rem;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .cam-video-wrapper {
            position: relative;
            background: #000;
            width: 100%;
            aspect-ratio: 16 / 9;
            overflow: hidden;
        }

        .cam-video-img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }

        .cam-controls-bar {
            padding: 0.6rem 1rem;
            background: rgba(0, 0, 0, 0.3);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border);
        }

        /* Incidents & Sidebar */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .panel-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
            backdrop-filter: blur(12px);
        }

        .panel-title {
            font-size: 1rem;
            font-weight: 700;
            color: #fff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .incidents-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            max-height: 580px;
            overflow-y: auto;
            padding-right: 0.3rem;
        }

        .incident-card {
            background: rgba(0, 0, 0, 0.35);
            border-left: 4px solid var(--cyan);
            border-radius: 6px;
            padding: 0.8rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            transition: all 0.2s;
        }

        .incident-card.sev-high { border-left-color: var(--red); }
        .incident-card.sev-medium { border-left-color: var(--amber); }

        .inc-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .inc-badge {
            padding: 0.15rem 0.45rem;
            border-radius: 4px;
            font-weight: 700;
            font-size: 0.7rem;
            text-transform: uppercase;
        }

        .badge-absence { background: rgba(239, 68, 68, 0.2); color: #f87171; }
        .badge-phone { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
        .badge-restricted { background: rgba(139, 92, 246, 0.2); color: #c084fc; }

        .inc-title {
            font-size: 0.88rem;
            font-weight: 600;
            color: #fff;
        }

        .inc-details {
            font-size: 0.78rem;
            color: #cbd5e1;
        }

        .inc-actions {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.3rem;
        }

        .btn-verify {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: #34d399;
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.72rem;
            cursor: pointer;
        }

        .btn-dismiss {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-size: 0.72rem;
            cursor: pointer;
        }

        .btn-verify:hover { background: var(--green); color: #000; }
        .btn-dismiss:hover { background: rgba(255, 255, 255, 0.15); color: #fff; }

        /* Modal Drawer for Zones */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(8px);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 100;
        }

        .modal-card {
            background: #0f172a;
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 90%;
            max-width: 900px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .modal-canvas-wrap {
            position: relative;
            width: 100%;
            aspect-ratio: 16 / 9;
            background: #000;
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
            cursor: crosshair;
        }

        #zoneCanvas {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
        }

        /* Pulse Dot */
        .dot-pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--green);
            display: inline-block;
            box-shadow: 0 0 8px var(--green);
        }
    </style>
</head>
<body>

    <!-- Header Navbar -->
    <header class="navbar">
        <div class="brand-box">
            <img src="/static/logo.png" alt="Al Noor Factory Logo" class="brand-logo" onerror="this.src='/static/factory_logo.jpg'">
            <div class="brand-titles">
                <h1>AI-CCTV Vision Platform</h1>
                <p>Al Noor Factory for Solar Panels | مصنع النور للألواح الشمسية</p>
            </div>
        </div>

        <div class="nav-actions">
            <span class="btn" style="border-color: rgba(16, 185, 129, 0.3); color: #34d399;">
                <span class="dot-pulse"></span> NVR Online (192.168.100.203)
            </span>
            <button class="btn btn-cyan" onclick="openEmployeesModal()">
                👥 Employees (إدارة الموظفين)
            </button>
        </div>
    </header>

    <div class="main-container">

        <!-- Top Stats Row -->
        <div class="stats-strip">
            <div class="stat-box">
                <div class="stat-label">Active Cameras</div>
                <div class="stat-val" id="stat-cams">--</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">AI Engine Speed</div>
                <div class="stat-val" id="stat-ai-fps">-- <span style="font-size: 0.9rem; color: var(--cyan);" id="stat-ai-device"></span></div>
            </div>
            <div class="stat-box">
                <div class="stat-label">System CPU & RAM</div>
                <div class="stat-val" id="stat-sys-load">--</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Unresolved Incidents</div>
                <div class="stat-val" style="color: var(--red);" id="stat-incidents">0</div>
            </div>
        </div>

        <!-- Main Workspace -->
        <div class="workspace-grid">

            <!-- Cameras Multi-Stream View -->
            <div class="cameras-section">
                <div class="section-header">
                    <span style="font-weight: 700; font-size: 1rem;">📹 Live Multi-Camera Stream (Pilot Phase 1)</span>
                    <div style="display: flex; gap: 0.5rem;">
                        <button class="btn" onclick="promptAddCamera()">+ Add Camera</button>
                    </div>
                </div>

                <div class="camera-views-grid" id="camerasGrid">
                    <!-- Dynamic Camera Cards will load here -->
                </div>
            </div>

            <!-- Incidents & Human Review Sidebar -->
            <div class="sidebar">
                <div class="panel-card">
                    <div class="panel-title">
                        <span>🚨 Live Safety & Rules Alerts</span>
                        <span style="font-size: 0.75rem; color: var(--text-muted);" id="incidentCountLabel">0 pending</span>
                    </div>

                    <div class="incidents-list" id="incidentsContainer">
                        <div style="text-align: center; color: var(--text-muted); padding: 2rem 0; font-size: 0.85rem;">
                            ✅ All monitored zones normal. No violations detected.
                        </div>
                    </div>
                </div>

                <div class="panel-card">
                    <div class="panel-title">
                        <span>⚙️ Quick AI Configuration</span>
                    </div>
                    <div style="display: flex; flex-direction: column; gap: 0.8rem; font-size: 0.82rem;">
                        <div>
                            <label style="color: var(--text-muted); display: flex; justify-content: space-between;">
                                <span>Worker Absence Timeout</span>
                                <span id="val-absence" style="color: var(--cyan);">120s</span>
                            </label>
                            <input type="range" min="30" max="600" step="10" value="120" style="width: 100%; margin-top: 0.3rem;"
                                   onchange="updateAbsenceThreshold(this.value)">
                        </div>

                        <div>
                            <label style="color: var(--text-muted); display: flex; justify-content: space-between;">
                                <span>Phone Alert Duration</span>
                                <span id="val-phone" style="color: var(--amber);">5s</span>
                            </label>
                            <input type="range" min="2" max="30" step="1" value="5" style="width: 100%; margin-top: 0.3rem;"
                                   onchange="updatePhoneThreshold(this.value)">
                        </div>
                    </div>
                </div>
            </div>

        </div>

    </div>

    <!-- Interactive Zone Drawer Modal -->
    <div class="modal-overlay" id="zoneModal">
        <div class="modal-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 id="modalCamTitle">✏️ Draw Polygonal Zone (Camera D14)</h3>
                <button class="btn" onclick="closeZoneModal()">✕ Close</button>
            </div>
            <p style="font-size: 0.82rem; color: var(--text-muted);">
                Click on the camera image below to place vertices. Select the zone type and click Save.
            </p>

            <div class="modal-canvas-wrap" id="canvasWrap">
                <canvas id="zoneCanvas"></canvas>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <label style="font-size: 0.82rem;">Zone Type:</label>
                    <select id="zoneTypeSelect" class="btn">
                        <option value="workstation">🟢 Workstation Zone (محطة عمل)</option>
                        <option value="restricted">🔴 Restricted Area (منطقة محظورة)</option>
                    </select>
                    <input type="text" id="zoneNameInput" class="btn" placeholder="Zone Name (e.g. Soldering Station 1)" style="width: 240px;">
                </div>

                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn" onclick="clearDrawnPoints()">🗑️ Clear Points</button>
                    <button class="btn btn-cyan" onclick="saveDrawnZone()">💾 Save Zone</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Employee Directory & Biometric Enrollment Modal -->
    <div class="modal-overlay" id="employeeModal">
        <div class="modal-card" style="max-width: 960px; max-height: 90vh; overflow-y: auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 0.8rem;">
                <h3 style="display: flex; align-items: center; gap: 0.5rem;">
                    👥 Employee Directory & Biometrics (دليل الموظفين والبصمات)
                </h3>
                <button class="btn" onclick="closeEmployeesModal()">✕ Close</button>
            </div>

            <!-- Enrollment Form -->
            <div style="background: rgba(0, 0, 0, 0.35); border: 1px solid var(--border); border-radius: 8px; padding: 1.2rem; display: flex; flex-direction: column; gap: 1rem;">
                <h4 style="color: var(--cyan); font-size: 0.92rem;">➕ Enroll New Worker with Biometric Face (تسجيل عامل جديد)</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                    <div>
                        <label style="font-size: 0.75rem; color: var(--text-muted);">Full Name (الاسم الكامل):</label>
                        <input type="text" id="empNameInput" class="btn" style="width: 100%; margin-top: 0.2rem;" placeholder="e.g. Ali Al-Khazali">
                    </div>
                    <div>
                        <label style="font-size: 0.75rem; color: var(--text-muted);">Employee Code (الرقم الوظيفي):</label>
                        <input type="text" id="empCodeInput" class="btn" style="width: 100%; margin-top: 0.2rem;" placeholder="e.g. EMP-101">
                    </div>
                    <div>
                        <label style="font-size: 0.75rem; color: var(--text-muted);">Department (القسم):</label>
                        <input type="text" id="empDeptInput" class="btn" style="width: 100%; margin-top: 0.2rem;" value="Solar Panel Assembly">
                    </div>
                    <div>
                        <label style="font-size: 0.75rem; color: var(--text-muted);">Assigned Station (محطة العمل):</label>
                        <select id="empZoneSelect" class="btn" style="width: 100%; margin-top: 0.2rem;">
                            <option value="">-- All Stations (Any) --</option>
                            <option value="z_14_workstation">Assembly Line 1 Workstation (Cam 14)</option>
                            <option value="z_15_workstation">Solar Cell Soldering Station (Cam 15)</option>
                        </select>
                    </div>
                </div>

                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.8rem;">
                    <div style="display: flex; align-items: center; gap: 0.8rem;">
                        <label class="btn" style="cursor: pointer; background: rgba(59, 130, 246, 0.2); border-color: var(--blue);">
                            📷 Select Face Photo...
                            <input type="file" id="empPhotoFile" accept="image/*" style="display: none;" onchange="handlePhotoSelect(this)">
                        </label>
                        <span id="photoFileName" style="font-size: 0.8rem; color: var(--text-muted);">No image chosen</span>
                    </div>

                    <button class="btn btn-cyan" onclick="submitEmployeeEnrollment()">
                        💾 Extract Biometrics & Save Worker
                    </button>
                </div>
                <div id="enrollStatusMsg" style="font-size: 0.82rem; display: none;"></div>
            </div>

            <!-- Existing Employees Roster Table -->
            <div style="display: flex; flex-direction: column; gap: 0.6rem;">
                <h4 style="font-size: 0.92rem; color: #fff;">📋 Registered Factory Workforce (<span id="empCountHeader">0</span>)</h4>
                <div id="employeesListContainer" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 0.8rem; max-height: 320px; overflow-y: auto;">
                    <!-- Cards will be populated dynamically -->
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentEditingCam = null;
        let drawnPoints = []; // normalized [ [x, y], ... ]
        let activeCamIds = [];
        let selectedEmpPhotoB64 = "";

        function openEmployeesModal() {
            document.getElementById('employeeModal').style.display = 'flex';
            fetchEmployees();
        }

        function closeEmployeesModal() {
            document.getElementById('employeeModal').style.display = 'none';
        }

        function handlePhotoSelect(input) {
            const file = input.files[0];
            if (!file) return;
            document.getElementById('photoFileName').textContent = file.name;
            const reader = new FileReader();
            reader.onload = function(e) {
                selectedEmpPhotoB64 = e.target.result;
            };
            reader.readAsDataURL(file);
        }

        async function fetchEmployees() {
            try {
                const res = await fetch('/api/employees');
                const list = await res.json();
                document.getElementById('empCountHeader').textContent = list.length;
                const container = document.getElementById('employeesListContainer');

                if (list.length === 0) {
                    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--text-muted);">No employees registered yet. Enroll workers above.</div>`;
                    return;
                }

                container.innerHTML = list.map(emp => `
                    <div style="background: rgba(0, 0, 0, 0.4); border: 1px solid var(--border); border-radius: 8px; padding: 0.8rem; display: flex; align-items: center; justify-content: space-between; gap: 0.8rem;">
                        <div style="display: flex; align-items: center; gap: 0.8rem;">
                            <img src="${emp.photo_path || '/static/logo.png'}" style="width: 44px; height: 44px; border-radius: 50%; object-fit: cover; border: 1px solid var(--cyan);" onerror="this.src='/static/logo.png'">
                            <div>
                                <div style="font-weight: 700; font-size: 0.88rem; color: #fff;">${escapeHtml(emp.full_name)}</div>
                                <div style="font-size: 0.75rem; color: var(--cyan); font-family: 'Fira Code', monospace;">${escapeHtml(emp.employee_code)} • ${escapeHtml(emp.department)}</div>
                                <div style="font-size: 0.72rem; color: var(--text-muted);">${emp.assigned_zone_id ? 'Station: ' + escapeHtml(emp.assigned_zone_id) : 'All Stations'}</div>
                            </div>
                        </div>
                        <button class="btn" style="color: var(--red); padding: 0.3rem 0.6rem; font-size: 0.75rem;" onclick="deleteEmployee(${emp.id})">🗑️</button>
                    </div>
                `).join('');
            } catch (err) {
                console.error("Error loading employees:", err);
            }
        }

        async function submitEmployeeEnrollment() {
            const name = document.getElementById('empNameInput').value.trim();
            const code = document.getElementById('empCodeInput').value.trim();
            const dept = document.getElementById('empDeptInput').value.trim();
            const zone = document.getElementById('empZoneSelect').value;
            const msgBox = document.getElementById('enrollStatusMsg');

            if (!name || !code) {
                alert("Please enter both Full Name and Employee Code.");
                return;
            }
            if (!selectedEmpPhotoB64) {
                alert("Please select a clear photo containing the employee's face.");
                return;
            }

            msgBox.style.display = 'block';
            msgBox.style.color = 'var(--cyan)';
            msgBox.textContent = "⏳ Extracting biometric facial embedding and saving profile...";

            try {
                const res = await fetch('/api/employees/enroll', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        full_name: name,
                        employee_code: code,
                        department: dept,
                        assigned_zone_id: zone || null,
                        photo_base64: selectedEmpPhotoB64
                    })
                });

                const data = await res.json();
                if (res.ok) {
                    msgBox.style.color = 'var(--green)';
                    msgBox.textContent = `✅ Successfully enrolled ${name} with biometric face recognition!`;
                    document.getElementById('empNameInput').value = '';
                    document.getElementById('empCodeInput').value = '';
                    document.getElementById('photoFileName').textContent = 'No image chosen';
                    selectedEmpPhotoB64 = '';
                    fetchEmployees();
                } else {
                    msgBox.style.color = 'var(--red)';
                    msgBox.textContent = `❌ Enrollment Error: ${data.detail || 'Failed'}`;
                }
            } catch (err) {
                msgBox.style.color = 'var(--red)';
                msgBox.textContent = `❌ Network Error: ${err.message}`;
            }
        }

        async function deleteEmployee(empId) {
            if (confirm("Delete this employee and their biometric face profile?")) {
                await fetch(`/api/employees/${empId}/delete`, { method: 'POST' });
                fetchEmployees();
            }
        }

        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                document.getElementById('stat-cams').textContent = `${data.cameras.length} Streams`;
                document.getElementById('stat-ai-fps').innerHTML = `${data.ai_fps} <span style="font-size: 0.8rem; color: var(--text-muted);">FPS</span>`;
                document.getElementById('stat-ai-device').textContent = `[${data.device}]`;
                document.getElementById('stat-sys-load').textContent = `CPU ${data.cpu_percent}% | RAM ${data.ram_percent}%`;
                document.getElementById('stat-incidents').textContent = data.pending_incidents;

                // Sync Cameras
                const newCamIds = data.cameras.map(c => c.cam_id);
                if (JSON.stringify(newCamIds) !== JSON.stringify(activeCamIds)) {
                    activeCamIds = newCamIds;
                    renderCamerasGrid(data.cameras);
                }
            } catch (err) {
                console.error("Telemetry error:", err);
            }
        }

        function renderCamerasGrid(cameras) {
            const grid = document.getElementById('camerasGrid');
            if (cameras.length === 0) {
                grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">No active camera streams. Click "+ Add Camera".</div>`;
                return;
            }

            grid.innerHTML = cameras.map(c => `
                <div class="cam-card">
                    <div class="cam-card-header">
                        <span class="cam-title">
                            <span class="dot-pulse"></span> Camera D${c.cam_id}
                        </span>
                        <span style="font-size: 0.75rem; color: var(--cyan); font-family: 'Fira Code', monospace;">
                            Stream ${c.suffix === '01' ? 'MAIN' : 'SUB'} | ${c.resolution} | ${c.fps} FPS
                        </span>
                    </div>

                    <div class="cam-video-wrapper">
                        <img src="/api/stream/${c.cam_id}" class="cam-video-img" alt="Camera D${c.cam_id}">
                    </div>

                    <div class="cam-controls-bar">
                        <button class="btn" style="font-size: 0.75rem;" onclick="openZoneModal(${c.cam_id})">
                            ✏️ Edit Zones
                        </button>
                        <div style="display: flex; gap: 0.4rem;">
                            <button class="btn" style="font-size: 0.75rem;" onclick="switchStreamType(${c.cam_id}, '${c.suffix === '01' ? '02' : '01'}')">
                                🔄 ${c.suffix === '01' ? 'Switch Sub' : 'Switch Main'}
                            </button>
                            <button class="btn" style="font-size: 0.75rem; color: var(--red);" onclick="removeCam(${c.cam_id})">
                                ✕
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        async function fetchIncidents() {
            try {
                const res = await fetch('/api/incidents');
                const list = await res.json();
                const container = document.getElementById('incidentsContainer');
                
                const pending = list.filter(i => i.status === 'pending');
                document.getElementById('incidentCountLabel').textContent = `${pending.length} pending`;

                if (list.length === 0) {
                    container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 2rem 0; font-size: 0.85rem;">✅ All monitored zones normal. No violations.</div>`;
                    return;
                }

                container.innerHTML = list.slice(0, 15).map(inc => {
                    let badgeCls = 'badge-absence';
                    if (inc.event_type === 'phone') badgeCls = 'badge-phone';
                    else if (inc.event_type === 'restricted') badgeCls = 'badge-restricted';

                    return `
                        <div class="incident-card sev-${inc.severity}">
                            <div class="inc-top">
                                <span class="inc-badge ${badgeCls}">${inc.event_type}</span>
                                <span>CAM D${inc.cam_id} • ${inc.timestamp.split(' ')[1]}</span>
                            </div>
                            <div class="inc-title">${escapeHtml(inc.title)}</div>
                            <div class="inc-details">${escapeHtml(inc.details)}</div>
                            ${inc.status === 'pending' ? `
                                <div class="inc-actions">
                                    <button class="btn-verify" onclick="reviewIncident('${inc.id}', 'verified')">✓ Verify (تأكيد)</button>
                                    <button class="btn-dismiss" onclick="reviewIncident('${inc.id}', 'dismissed')">✗ False Alarm</button>
                                </div>
                            ` : `
                                <div style="font-size: 0.72rem; color: ${inc.status === 'verified' ? '#34d399' : '#94a3b8'}; margin-top: 0.2rem;">
                                    ${inc.status === 'verified' ? '✓ Verified Incident' : '✗ Dismissed (False Alarm)'}
                                </div>
                            `}
                        </div>
                    `;
                }).join('');
            } catch (err) {
                console.error("Incidents fetch error:", err);
            }
        }

        async function reviewIncident(id, action) {
            await fetch(`/api/incidents/${id}/action`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action })
            });
            fetchIncidents();
        }

        async function promptAddCamera() {
            const raw = prompt("Enter Camera Channel number (e.g. 14, 15, 16):");
            if (raw) {
                const clean = parseInt(raw.replace(/\D/g, ''));
                if (clean > 0) {
                    await fetch('/api/cameras/switch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ cam_id: clean, suffix: '01' })
                    });
                    fetchTelemetry();
                }
            }
        }

        async function removeCam(camId) {
            if (confirm(`Remove Camera D${camId} from active monitoring?`)) {
                await fetch('/api/cameras/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ cam_id: camId })
                });
                fetchTelemetry();
            }
        }

        async function switchStreamType(camId, newSuffix) {
            await fetch('/api/cameras/switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cam_id: camId, suffix: newSuffix })
            });
            fetchTelemetry();
        }

        // Zone Drawer Logic
        function openZoneModal(camId) {
            currentEditingCam = camId;
            drawnPoints = [];
            document.getElementById('modalCamTitle').textContent = `✏️ Draw Polygonal Zone (Camera D${camId})`;
            document.getElementById('zoneModal').style.display = 'flex';
            
            const canvas = document.getElementById('zoneCanvas');
            const wrap = document.getElementById('canvasWrap');
            canvas.width = wrap.clientWidth;
            canvas.height = wrap.clientHeight;
            
            drawZoneCanvas();
        }

        function closeZoneModal() {
            document.getElementById('zoneModal').style.display = 'none';
        }

        const canvas = document.getElementById('zoneCanvas');
        canvas.addEventListener('click', (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = (e.clientX - rect.left) / rect.width;
            const y = (e.clientY - rect.top) / rect.height;
            drawnPoints.push([parseFloat(x.toFixed(3)), parseFloat(y.toFixed(3))]);
            drawZoneCanvas();
        });

        function clearDrawnPoints() {
            drawnPoints = [];
            drawZoneCanvas();
        }

        function drawZoneCanvas() {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            if (drawnPoints.length === 0) return;

            ctx.beginPath();
            ctx.strokeStyle = '#06b6d4';
            ctx.fillStyle = 'rgba(6, 182, 212, 0.25)';
            ctx.lineWidth = 3;

            drawnPoints.forEach((p, idx) => {
                const px = p[0] * canvas.width;
                const py = p[1] * canvas.height;
                if (idx === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);

                // Draw vertex dot
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(px - 4, py - 4, 8, 8);
                ctx.fillStyle = 'rgba(6, 182, 212, 0.25)';
            });

            if (drawnPoints.length >= 3) {
                ctx.closePath();
                ctx.fill();
            }
            ctx.stroke();
        }

        async function saveDrawnZone() {
            if (drawnPoints.length < 3) {
                alert("Please click at least 3 points on the screen to form a polygon zone.");
                return;
            }
            const zType = document.getElementById('zoneTypeSelect').value;
            const zName = document.getElementById('zoneNameInput').value.trim() || `${zType} Zone`;

            const newZone = {
                id: `zone_${currentEditingCam}_${Date.now()}`,
                name: zName,
                type: zType,
                polygon: drawnPoints
            };

            // Fetch existing zones for camera
            const curRes = await fetch(`/api/zones/${currentEditingCam}`);
            let curZones = await curRes.json();
            if (!Array.isArray(curZones)) curZones = [];
            curZones.push(newZone);

            await fetch(`/api/zones/${currentEditingCam}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(curZones)
            });

            alert(`✅ Zone "${zName}" saved successfully!`);
            closeZoneModal();
        }

        async function updateAbsenceThreshold(val) {
            document.getElementById('val-absence').textContent = val + 's';
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ absence_threshold_sec: parseInt(val) })
            });
        }

        async function updatePhoneThreshold(val) {
            document.getElementById('val-phone').textContent = val + 's';
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_duration_sec: parseInt(val) })
            });
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        // Init loops
        fetchTelemetry();
        fetchIncidents();
        setInterval(fetchTelemetry, 2500);
        setInterval(fetchIncidents, 3000);
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import webbrowser
    port = 8000
    url = f"http://127.0.0.1:{port}"
    print(f"\n=======================================================")
    print(f"  AI-CCTV Vision Platform — Al Noor Solar Factory")
    print(f"  Web Dashboard: {url}")
    print(f"  Interactive API Docs: {url}/docs")
    print(f"=======================================================\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="0.0.0.0", port=port)
