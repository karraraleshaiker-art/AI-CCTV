# AI-CCTV Agent Handoff

This repository is for the AI-CCTV factory monitoring prototype. Keep the work practical and incremental: one stable real factory camera first, then add features only after the previous layer works reliably on-site.

## Operating Rules

- Do not commit NVR usernames, passwords, full RTSP URLs with credentials, `.env` files, `config.local.json`, recordings, face images, event evidence, model weights, or `.venv`.
- Treat anything under `sources/` as read-only reference material if this repo is opened from a ChatGPT project mirror.
- The factory AI server keeps runtime-only files locally: `.venv`, downloaded YOLO weights, credentials, output videos/images, and logs.
- Prefer small, testable changes. Do not add posture, face recognition, dashboards, or multi-camera processing until the stable core is proven on D14.
- When changing camera/RTSP code, preserve credential prompting or local-only config. Use placeholders in docs and examples.
- If an NVR credential appears in history, assume it is compromised and ask the user to rotate it. Do not repeat it.

## Current Direction

The current engineering direction is a controlled software reset, not a restart of the whole project.

Stable core target:

1. D14 RTSP camera connection.
2. Smooth live view using a latest-frame capture thread.
3. YOLO11s person detection on resized inference frames.
4. ByteTrack or equivalent stable tracking IDs.
5. Phone detection.
6. Live camera switching while processing only one camera at a time.
7. CPU/RAM/AI FPS/inference-time monitoring.

Do not rebuild the overloaded v0.3 style pipeline in one step. The prior stack tried to run detection, pose, tracking, face capture/recognition, phone logic, video writing, overlays, and monitoring on CPU-only hardware and dropped to about 3-4 AI FPS with lag/glitches.

## Development Rule

Do not add Step N+1 until Step N works reliably on the real factory camera.

Recommended branch/version path:

- `v0.1-camera`: RTSP stable live view.
- `v0.2-person-detection`: people detected reliably on D14.
- `v0.3-tracking`: stable temporary IDs.
- `v0.4-phone`: phone detection and phone-use confirmation.
- Later: event recording, posture, persistent identity, multi-camera support, dashboard.

## Known Factory Setup

- Project folder used on the AI PC: `C:\AI-CCTV\project`.
- Launcher requirement: double-clickable Windows batch file, no manual virtual-environment activation for normal use.
- Main pilot camera: Hikvision/NVR channel D14.
- NVR LAN address observed in testing: `192.168.100.203`.
- RTSP port: `554`.
- Hikvision channel convention:
  - D14 main stream: `/Streaming/channels/1401`
  - D14 sub-stream: `/Streaming/channels/1402`
- RTSP template only:
  - `rtsp://<USERNAME>:<PASSWORD>@192.168.100.203:554/Streaming/channels/1401`
  - Never commit a filled-in URL.

## Hardware/Runtime Notes

- Windows 11 AI PC.
- Python: `3.12.10`.
- CPU: Intel Core i7-14700F, 28 logical CPUs.
- RAM: about 15.8 GB.
- GPU/CUDA in current environment: none available to PyTorch.
- PyTorch currently runs CPU-only.
- A GT 730 was mentioned/observed as not useful for CUDA acceleration.
- OpenVINO may be worth testing later for Intel CPU acceleration, after the stable core works.

## Important Prior Failures

- Running YOLO11n on D14 sub-stream worked, but the sub-stream was too low-resolution and falsely detected a fire extinguisher as a person.
- D14 main stream is clearer but H.265 decoding through OpenCV/FFmpeg produced errors such as `PPS id out of range`, `Could not find ref with POC`, and `cu_qp_delta ... outside valid range`.
- Use `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp` before Python in the batch launcher to reduce RTSP/HEVC stream issues.
- If H.265 remains unstable, consider configuring the AI stream as H.264 on the NVR.
- A prior OpenCV build lacked `cv2.CascadeClassifier`, causing a crash in face-capture initialization. Face capture must be optional or use a more reliable detector.
- A nested virtual environment was accidentally created under `.venv\Scripts\.venv`; avoid working inside `.venv`.
- Persistent person ID logic failed badly in earlier versions: about 90 person records were created for only about 3 real workers because tracking was lost repeatedly.

## Source Availability Warning

The ChatGPT project mirror contained `sources/project 1.zip`, but that archive only showed:

- `requirements.txt`
- `yolo11n.pt`

It did not contain the latest v0.4 source files. If the GitHub repo or factory AI PC has a fuller version, inspect that before replacing anything. Useful older filenames mentioned in the conversation include `main.py`, `face_engine.py`, `event_recorder.py`, `settings.json`, `tracker_factory.yaml`, `requirements.txt`, `run_ai_cctv.bat`, and `README.txt`.

## Validation Expectations

For each version, test on D14 at the factory and record:

- AI FPS.
- Inference time.
- CPU/RAM use.
- Whether live view is delayed, glitchy, or near real time.
- Number of real workers visible versus detected.
- Whether chair/fire extinguisher false positives remain.
- Whether seated/stationary/far/partially hidden workers remain detected.
- Whether IDs remain stable during occlusion and short detection dropouts.
