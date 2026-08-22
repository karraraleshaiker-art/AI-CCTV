# AI-CCTV Project Context

AI-CCTV is a factory monitoring prototype for Hikvision/NVR camera streams. The immediate goal is not a polished final product; it is a stable, understandable core that works on the real factory camera before adding heavier features.

## Current Decision

Do not restart the whole project from zero, and do not continue stacking features onto the overloaded prototype. Use a controlled software reset:

- Keep old `v0.1` to `v0.4` experiments as reference.
- Rebuild the production candidate gradually.
- Treat GitHub as the official source-code history, not as a backup of the whole AI server.

## Known Architecture

The intended stable-core architecture is:

```text
Hikvision/NVR RTSP stream
        ↓
background capture thread
        ↓
latest frame only, no growing queue
        ↓
live display remains near real time
        ↓
YOLO runs separately on newest available frame
        ↓
person detection
        ↓
tracking IDs
        ↓
phone detection
        ↓
event logic later
```

The key design fix is to avoid frame backlog. If AI inference only reaches 4-8 FPS, the displayed stream should still stay close to live by dropping old frames instead of processing a stale queue.

## Factory Hardware And Runtime

- AI PC OS: Windows 11.
- Project path used on AI PC: `C:\AI-CCTV\project`.
- Python: `3.12.10`.
- CPU: Intel Core i7-14700F, 28 logical CPUs.
- RAM: about 15.8 GB.
- Disk observed by `yolo checks`: about 520 GB total.
- Current PyTorch mode: CPU-only.
- CUDA/GPU: not available in the current Python environment.
- A GT 730-class GPU was mentioned and should not be relied on for modern YOLO acceleration.
- Python environment: local `.venv` under the project folder.
- Normal launch workflow should be `run_ai_cctv.bat`, double-clicked by the user.

## Python Dependencies Observed

The uploaded `requirements.txt` included:

- `ultralytics==8.4.123`
- `torch==2.13.0`
- `torchvision==0.28.0`
- `opencv-python==5.0.0.93`
- `numpy==2.5.2`
- `psutil==7.2.2`
- `PyYAML==6.0.3`
- `requests==2.34.2`
- `nvidia-ml-py==13.610.43`

Do not assume these versions are ideal; they are the environment snapshot that worked well enough for initial tests.

## NVR And Camera Details

- NVR LAN IP observed during testing: `192.168.100.203`.
- RTSP port: `554`.
- Camera system: Hikvision NVR/cameras.
- Pilot camera: D14.
- D14 main stream:
  - channel path: `/Streaming/channels/1401`
  - resolution: `2560 x 1440`
  - frame rate: `25 FPS`
  - codec: `H.265 / HEVC`
  - bitrate: roughly `1-3 Mbps`
  - lens noted by user: likely `2.8 mm`
- D14 sub-stream:
  - channel path: `/Streaming/channels/1402`
  - approximate resolution: `640 x 360`
  - judged too low-resolution for the main detection target.

Use RTSP templates only:

```text
rtsp://<USERNAME>:<PASSWORD>@192.168.100.203:554/Streaming/channels/1401
rtsp://<USERNAME>:<PASSWORD>@192.168.100.203:554/Streaming/channels/1402
```

Never commit a real username, password, or filled-in RTSP URL.

## Factory Scene

D14 is mounted high near the ceiling and looks downward. The camera sees machinery/workstations where workers may:

- stand, sit, or bend over machines;
- stay completely still while working;
- overlap or partially hide each other;
- appear at different scales and distances;
- hold phones at face/chest level or low near the machine/table.

Normal visible worker count is around 3, but the system should tolerate up to about 7. Reliable detection is needed out to roughly 5 meters or less.

Known visual challenges:

- two close workers sometimes merge into one detection;
- chairs and fire extinguishers can look person-like to the detector;
- distant, seated, stationary, or partially hidden workers can disappear;
- phone objects can be small in the 4 MP frame.

## Product Requirements

Immediate stable-core requirements:

- process one selected camera at a time;
- prompt for NVR username/password at runtime or use local-only config;
- allow the user to choose camera/channel at startup;
- support main/sub-stream choice, but optimize first for D14 main stream;
- show a live camera window with detections;
- quit cleanly with `Q`/Esc;
- show CPU, RAM, AI FPS, and inference time while running;
- support live camera switching later without processing multiple cameras simultaneously.

Detection requirements:

- detect workers as people even when seated, stationary, far, or partially hidden;
- prefer not missing real workers over aggressively hiding every possible false positive;
- still suppress obvious static false objects conservatively;
- keep temporary IDs stable during short detection dropouts and occlusion;
- do not generate a new permanent person every time tracking flickers.

Phone-use requirements for later event layer:

- detect phone use whether the phone is high near the face/chest or low near the machine/table;
- start an official phone event only after continuous phone detection for 2 seconds;
- keep the event alive if the phone briefly disappears;
- end phone use after 5 seconds without phone detection;
- save 5 seconds before initial phone detection and 5 seconds after the event closes;
- save both original and annotated event videos during development;
- save one best evidence image per event;
- log each event to `events.csv` and `event.json`;
- no event ID should clutter the live view.

Identity requirements for later:

- temporary IDs should look like `T001`, `T002`, etc.
- permanent IDs should look like `P0001`, `P0002`, etc.
- do not use clothing/body appearance for persistent identity.
- only save clear front-facing faces.
- if a better frontal face is captured later, replace the old face image.
- use strict face matching; if uncertain, keep the person temporary/unknown.
- permanent IDs should persist across app restart once face recognition is implemented.

Posture requirements for later:

- states should be `MOVING`, `STANDING`, `SITTING`, or `UNKNOWN`.
- `MOVING` means real location change/walking, not arm movement while working.
- If posture is uncertain, display `UNKNOWN` rather than guessing.

## Previous Experiments And Problems

Initial proof:

- RTSP from D14 reached YOLO.
- YOLO11n could detect people on the live stream.
- The Python virtual environment worked.
- The batch-file launch workflow worked.

Problems found:

- D14 sub-stream was too low-resolution and produced weak detections.
- A fire extinguisher and chair were sometimes detected as people.
- YOLO11n was too weak for the factory view.
- A later feature-heavy version overloaded CPU-only processing and dropped to about 3-4 AI FPS.
- OpenCV/FFmpeg had H.265 decode warnings/errors on the main stream:
  - `PPS id out of range`
  - `Could not find ref with POC`
  - `cu_qp_delta ... outside valid range`
- Face capture crashed when `cv2.CascadeClassifier` was not available.
- Tracking/person identity became unstable and created many person IDs for a few real workers.
- Face snapshots from behind/poor angles were not useful and should be avoided.

## Stable-Core Development Plan

1. Camera connection and smooth live view.
   - Use D14 main stream first.
   - Use RTSP over TCP via `OPENCV_FFMPEG_CAPTURE_OPTIONS=rtsp_transport;tcp`.
   - If H.265 remains unstable, consider a dedicated H.264 AI stream on the NVR.

2. Person detection.
   - Use YOLO11s as the default next model.
   - Benchmark YOLO11s at 640 input first; try 768 only if performance allows.
   - Keep boxes mapped correctly back onto the display frame.

3. Stable tracking.
   - Use ByteTrack or a proven tracker.
   - Preserve temporary IDs during brief detection dropouts.
   - Avoid creating permanent person records from unstable tracks.

4. Phone detection.
   - Associate phone boxes with nearby worker boxes.
   - Apply 2-second confirmation before creating a phone event.
   - Apply 5-second phone-loss grace before ending an event.

5. Event recording.
   - Add rolling frame buffer.
   - Save original and annotated event videos, best evidence image, `event.json`, and `events.csv`.

6. Posture.
   - Add pose model only after stable person and phone layers are working.

7. Persistent identity.
   - Add strict frontal-face recognition only after tracking is reliable.
   - Avoid saving bad/side/back face crops.

8. Multiple cameras.
   - First add live switching between cameras while processing one camera at a time.
   - Only later consider simultaneous multi-camera processing.

9. Dashboard/database.
   - Start with folders, CSV, and JSON.
   - Move to SQLite/dashboard only after event logic is trusted.

## Suggested Repository Hygiene

Commit source/config templates only:

```text
main.py
settings.example.json
run_ai_cctv.bat
requirements.txt
README.md
PROJECT_CONTEXT.md
AGENTS.md
.gitignore
```

Do not commit:

```text
.venv/
*.pt
*.onnx
config.local.json
.env
output/
runs/
recordings/
*.mp4
*.avi
*.mkv
face images
event evidence
RTSP URLs with credentials
```

## Security Notes

- A real NVR credential was accidentally pasted in the prior conversation. It should be rotated on the NVR and updated locally on the AI PC.
- Keep the factory CCTV/NVR network separated from public development access unless company/IT approval exists.
- GitHub should contain code and templates, not operational evidence or secrets.
- Any future remote-agent access to the AI PC should be explicitly approved and tightly limited.
