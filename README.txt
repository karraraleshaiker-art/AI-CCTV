AI CCTV v0.4 — STABLE CORE
=============================

This version intentionally removes the heavy features that made v0.3 lag.

It does ONLY:
- RTSP live capture
- YOLO11s person detection
- YOLO11s phone detection
- ByteTrack IDs
- live camera switching
- CPU/RAM/AI FPS monitoring

Important architecture change:
RTSP capture runs continuously in its own thread and keeps ONLY the newest frame.
AI runs independently on the newest available frame. Old frames are discarded.
This prevents a growing RTSP backlog when AI is slower than the camera.

NO pose, face recognition, permanent IDs, or event recording yet.

First run may download yolo11s.pt automatically.

Controls:
Q / ESC = quit
N = next camera
P = previous camera
C = choose camera in CMD

Recommended first test:
Camera D14
MAIN stream

Judge only:
1. Is live video close to real time?
2. What AI FPS is shown?
3. How many real people are visible vs detected?
4. Does chair/fire extinguisher still become a person?

Keep your existing .venv. Copy these files into that project folder and
double-click run_ai_cctv.bat.
