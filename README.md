# AI CCTV Monitor

Live CCTV monitoring for two events:

- a person appears to be using a phone
- a tracked person leaves the place/zone you define

The system accepts a webcam index, video file, RTSP URL, or HTTP camera stream, runs object detection, tracks people frame to frame, and serves a small dashboard with a live annotated feed.

Alerts are saved to disk with optional evidence images, so the operator can review what happened after the live moment has passed.

## Quick Start

Use Python 3.11 or 3.12 for best compatibility with OpenCV and Ultralytics.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy config.example.json config.json
python -m cctv_ai.app --config config.json
```

Open the dashboard:

```text
http://127.0.0.1:8000
```

## Easy NVR Launcher

Double-click:

```text
run_nvr_ai.bat
```

It asks for:

- NVR username
- NVR password

It uses the saved camera settings: NVR `192.168.100.203`, channel `14`, main stream, Hikvision RTSP path `/Streaming/Channels/1401`. Then it opens the dashboard and starts processing the NVR camera. Keep the batch window open while the system is running. Press `CTRL+C` in that window to stop it.

The launcher checks for Python packages first. If `.venv` is missing, it creates it. If required packages are missing, it installs `requirements.txt`. The NVR password is typed at launch time and is not saved to the repo.

To test only the camera connection before starting AI, double-click:

```text
test_nvr_connection.bat
```

## Camera Input

The normal input is the CCTV/NVR RTSP stream. The AI processing runs on this computer; the NVR only provides the video stream.

Current target NVR input:

```text
rtsp://192.168.100.203:554/Streaming/Channels/1401
```

That is channel 14 main stream. VLC can open this URL and ask for username/password in a popup. The Python AI app cannot show VLC's RTSP login popup, so `run_nvr_ai.bat` asks for the NVR username and password before it starts OpenCV.

Create your local config:

```powershell
copy config.nvr.example.json config.local.json
notepad config.local.json
```

Set these fields:

- `nvr_host`: your NVR IP, for example `192.168.100.203`
- `nvr_port`: usually `554`
- `nvr_username`: the NVR username
- `nvr_password`: the NVR password
- `nvr_channel`: the camera channel on the NVR, currently `14`
- `nvr_stream`: `main` or `sub`
- `nvr_url_style`: `hikvision`, `dahua`, or `generic`

Then run:

```powershell
.\.venv\Scripts\python.exe -m cctv_ai.app --config config.local.json
```

The dashboard will show the RTSP source with the password hidden. If you need to test from a laptop webcam or a video file, set `camera_source` explicitly:

```json
{
  "camera_source": "0"
}
```

Common RTSP paths:

- Your Hikvision-style channel 14 main stream: `/Streaming/Channels/1401`
- Your Hikvision-style channel 14 substream: `/Streaming/Channels/1402`
- Hikvision-style channel 1 main stream: `/Streaming/Channels/101`
- Hikvision-style channel 1 substream: `/Streaming/Channels/102`
- Hikvision-style channel 2 main stream: `/Streaming/Channels/201`
- Hikvision-style channel 2 substream: `/Streaming/Channels/202`
- Dahua-style channel 1 main stream: `/cam/realmonitor?channel=1&subtype=0`
- Dahua-style channel 1 substream: `/cam/realmonitor?channel=1&subtype=1`

If your NVR uses stream names like `0.1` for main and `0.2` for substream, test this shape:

```text
rtsp://USERNAME:PASSWORD@192.168.100.203:554/0.1
rtsp://USERNAME:PASSWORD@192.168.100.203:554/0.2
```

You can probe an RTSP URL before starting the web dashboard:

```powershell
.\.venv\Scripts\python.exe -m tools.rtsp_probe --config config.local.json
.\.venv\Scripts\python.exe -m tools.rtsp_probe --template hikvision --channel 14 --stream main --username admin
.\.venv\Scripts\python.exe -m tools.rtsp_probe --template hikvision --channel 14 --stream sub --username admin
.\.venv\Scripts\python.exe -m tools.rtsp_probe --template generic --stream main --username admin
```

## Define The Place

In the dashboard, click **Edit Zone**, then click points on the video to draw the allowed place. Click **Save Zone** when finished.

Zone points are stored in `runtime_state.json` as normalized coordinates, so they continue to work if the stream size changes.

## Alert Review

When the AI detects phone use or a confirmed person leaving the assigned place, it:

- adds a live alert to the dashboard
- saves the alert history to `output/alerts/alerts.jsonl`
- saves an evidence image to `output/evidence/`
- lets the operator acknowledge the alert from the dashboard

If an RTSP/NVR stream stops returning frames, the pipeline keeps the dashboard running and periodically reconnects to the camera.

## Performance Notes

The NVR main stream is `2560x1440`. The default AI processing profile now keeps more detail for far people by resizing frames to `1280` pixels wide, running YOLO at `960` image size, lowering detection confidence to `0.25`, targeting `20` FPS, and using JPEG quality `85` for the browser stream.

If the processed FPS stays below the target, the model is the bottleneck even if Windows Task Manager does not show 100% CPU/GPU. For more speed, reduce `model_imgsz` to `736` or `640`. For better far-person detection, raise `model_imgsz` to `1280`, but expect lower FPS.

## Detection Notes

The default model is `yolov8n.pt`, which can detect `person` and `cell phone` from the COCO dataset. Phone-use detection is a practical heuristic: if a cell phone is detected inside or near the upper part of a person bounding box for several frames, the system raises a phone alert.

For production, improve accuracy by training a dedicated "phone usage" model using real CCTV angles from your site.

## Files

- `cctv_ai/app.py`: FastAPI server and API routes
- `cctv_ai/pipeline.py`: video processing loop
- `cctv_ai/detector.py`: YOLO object detector
- `cctv_ai/tracker.py`: lightweight person tracker
- `cctv_ai/zones.py`: polygon/zone logic
- `cctv_ai/alerts.py`: event persistence and cooldown handling
- `static/`: browser dashboard

## Run Checks

```powershell
python -m compileall cctv_ai
python -m pytest
```
