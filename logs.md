# AI-CCTV Project Documentation & Changelog

---

# Section 1: Project Overview & Scope

### System Context: Solar Panel Manufacturing Facility
The **AI-CCTV** system is an intelligent, automated computer vision and compliance monitoring platform designed specifically for the **Solar Panel Manufacturing Factory**. The facility operates approximately **40–45 high-resolution CCTV cameras** connected through an enterprise Network Video Recorder (**NVR**) infrastructure over the **RTSP** protocol.

### Primary Objectives
1. **Automated Compliance & Safety Monitoring**: Detect critical workplace events in real-time without constant manual surveillance:
   - **Workstation Absence**: Timed tracking of operator presence in designated manufacturing assembly stations.
   - **Mobile Phone Usage**: Real-time detection of unauthorized smartphone interaction during active production cycles.
   - **Restricted Area Breach**: Boundary and virtual tripwire enforcement for hazardous equipment zones.
   - **Occupancy & Crowd Density**: Monitoring safe headcounts in sensitive production clusters.
   - **Camera Stream Health**: Instant alerting upon RTSP feed disconnection or signal degradation.
2. **Decoupled Low-Latency Architecture**: Overcoming RTSP streaming lag through independent multithreaded capture and AI inference loops (`LatestFrameCapture` single-frame drop strategy).
3. **Human-in-the-Loop Verification**: AI identifies, prioritizes, and logs incidents with timestamped visual evidence, presenting them to authorized supervisors for final decision-making.

### Core Project Team
- **Ali Nasser** (Co-Founder & Lead Engineer)
- **Karrar Haider** (Co-Founder & Lead Engineer)

---

# Section 2: Purpose of `logs.md` & Logging Protocol

### Purpose
This document serves as the **Single Source of Truth (SSOT)** for all architectural decisions, code modifications, bug fixes, and feature additions across the project. Because development is conducted asynchronously by two collaborating engineers, strict logging prevents overlapping changes, resolves conflicts, and provides an auditable engineering trail.

### Collaborative Workflow Rules
1. **Single-Session Isolation**: Ali and Karrar work in mutually exclusive sessions. When one developer is actively coding, the other does not perform changes to avoid code branching collisions.
2. **Immediate GitHub Synchronization**: All changes must be committed and pushed immediately to the central repository: `https://github.com/karraraleshaiker-art/AI-CCTV`.
3. **Pre-Session Connectivity Check**: Before launching any session, internet connectivity is strictly verified to ensure the latest upstream commits are pulled.
4. **Mandatory Card Logging**: Every modification must be accompanied by a structured changelog entry card in **Section 3** below.

### Standard Card Template
Each changelog entry must strictly follow this structure:

```markdown
### [Log #ID] - <Short Summary of Change>
- **Author**: <Ali Nasser | Karrar Haider>
- **Timestamp**: <YYYY-MM-DD HH:MM:SS Timezone>
- **AI Agent**: <Antigravity | Codex | Other>
- **Objective / Purpose**: <Detailed explanation of why this change was made>
- **Affected Files**:
  - `[ADDED | MODIFIED | DELETED]` <path/to/file>
- **Line Changes Breakdown**:
  - `<file>`: Lines X–Y <Description of line additions, modifications, or deletions>
```

---

# Section 3: Chronological Changelog Entries

---

### [Log #001] - Initial Core Architecture Release (v0.4 Stable Core)
- **Author**: Karrar Haider & Ali Nasser
- **Timestamp**: 2026-08-22 01:00:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**: 
  - Established the foundational v0.4 Stable Core engine.
  - Eliminated high-latency bottlenecks by implementing the `LatestFrameCapture` multithreaded single-frame queue strategy.
  - Integrated YOLO11s object detection model with ByteTrack tracking for `person` (Class 0) and `cell phone` (Class 67).
  - Built interactive CLI camera switching (`N`, `P`, `C`, `Q`) and live OpenCV video overlay.
- **Affected Files**:
  - `[ADDED]` `main.py`
  - `[ADDED]` `settings.json`
  - `[ADDED]` `run_ai_cctv.bat`
  - `[ADDED]` `sync_github.sh`
  - `[ADDED]` `README.txt`
  - `[ADDED]` `.gitignore`
- **Line Changes Breakdown**:
  - `main.py`: Lines 1–197 (Created full implementation including `LatestFrameCapture`, `AIWorker`, `draw`, and `startup` routines).
  - `settings.json`: Lines 1–12 (Defined NVR IP, RTSP port, confidence thresholds, image size, tracker configuration, and display resolution).
  - `run_ai_cctv.bat`: Lines 1–20 (Batch execution script for Windows with TCP transport flag).
  - `sync_github.sh`: Lines 1–24 (Initial GitHub pull/commit/push script).
  - `README.txt`: Lines 1–41 (Documented v0.4 scope and testing criteria).
  - `.gitignore`: Lines 1–10 (Basic Python virtual environment and cache ignores).

---

### [Log #002] - Factory Proposal Integration, Interactive Logs Reader & Multi-Platform Sync Automation
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 03:45:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Added the comprehensive Solar Panel Factory AI CCTV Monitoring Proposal (`AI_Assisted_CCTV_Monitoring_Proposal.docx`).
  - Created the standardized English `logs.md` system tracking all modifications and establishing collaboration protocol between Ali and Karrar.
  - Developed a standalone web-based `logs_reader.py` dashboard with live Markdown rendering, card search, and real-time auto-reload.
  - Upgraded `sync_github.sh` (for Karrar / Linux / Windows Git Bash) with mandatory pre-flight internet connectivity verification, upstream sync, and auto-launching of both the Logs Reader and Main CCTV engine.
  - Created `sync_github.command` (for Ali on macOS) with custom offline warnings, auto-sync, and app launcher.
  - Enhanced `.gitignore` to prevent committing model weight files (`*.pt`, `*.onnx`), logs, and macOS/IDE metadata.
- **Affected Files**:
  - `[ADDED]` `AI_Assisted_CCTV_Monitoring_Proposal.docx`
  - `[ADDED]` `logs.md`
  - `[ADDED]` `logs_reader.py`
  - `[ADDED]` `sync_github.command`
  - `[MODIFIED]` `sync_github.sh`
  - `[MODIFIED]` `.gitignore`
- **Line Changes Breakdown**:
  - `logs.md`: Lines 1–135 (Full project overview, collaboration framework, and changelog cards).
  - `logs_reader.py`: Lines 1–230 (Built lightweight zero-dependency Python HTTP server and interactive Glassmorphism web UI).
  - `sync_github.sh`: Lines 1–55 (Added internet check against `github.com` & `1.1.1.1`, warning alert for Ali, automatic pull, background Logs Reader launcher, and main app execution).
  - `sync_github.command`: Lines 1–55 (Executable macOS launcher with partner-specific warning for Karrar, auto-sync, Logs Reader, and app startup).
  - `.gitignore`: Lines 1–20 (Added ignore rules for `*.pt`, `*.onnx`, `*.engine`, `.DS_Store`, `.vscode/`, `.idea/`).

---

### [Log #003] - FastAPI Web Vision Platform, Factory Logo Integration, Interactive Zone Drawer & Launcher Separation
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 04:05:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Transitioned the entire system from traditional CLI / OpenCV desktop window to a modern, high-performance **FastAPI Web Platform** (`app.py`).
  - Analyzed and integrated the official Al Noor Factory logos (`logo.png` & `Al Noor Factory logo.jpg`) with solar teal/charcoal styling and branding.
  - Implemented multi-camera concurrent streaming (Pilot Phase 1: Cam 14 & Cam 15) with decoupled RTSP frame ingestion.
  - Built interactive browser-based **Polygonal Zone Drawer** enabling mouse-based creation of Workstation and Restricted safety zones.
  - Implemented temporal rules engine detecting workstation absence (>120s) and active phone violations (>5s) with live incident cards and supervisor verification buttons (`Verify` / `Dismiss`).
  - Separated `logs_reader.py` into an independent on-demand audit tool while updating `sync_github.command`, `sync_github.sh`, and `run_ai_cctv.bat` to launch the FastAPI web interface directly.
- **Affected Files**:
  - `[ADDED]` `app.py`
  - `[ADDED]` `static/logo.png`
  - `[ADDED]` `static/factory_logo.jpg`
  - `[MODIFIED]` `settings.json`
  - `[MODIFIED]` `sync_github.command`
  - `[MODIFIED]` `sync_github.sh`
  - `[MODIFIED]` `run_ai_cctv.bat`
  - `[MODIFIED]` `logs.md`
- **Line Changes Breakdown**:
  - `app.py`: Lines 1–850 (Built complete FastAPI backend, MJPEG multi-camera streaming, YOLO11 inference, rules engine, and embedded dashboard UI).
  - `settings.json`: Lines 1–42 (Added dual-camera configuration, zone schemas, and absence/phone alert thresholds).
  - `sync_github.command`: Lines 1–45 (Updated launcher to start FastAPI app.py on macOS).
  - `sync_github.sh`: Lines 1–45 (Updated launcher to start FastAPI app.py for Linux / Git Bash).
  - `run_ai_cctv.bat`: Lines 1–20 (Updated Windows runner to invoke app.py).
  - `logs.md`: Lines 110–148 (Added Log #003 entry).

---

### [Log #004] - Independent Dual-Process Launcher, Navbar Cleanup & FastAPI Lifespan Handler Migration
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 10:00:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Re-architected `sync_github.command` (macOS) and `sync_github.sh` (Linux/Git Bash) to launch both **Logs Reader** (port 8808) and **AI CCTV Platform** (port 8000) as separate independent background/foreground processes.
  - Enabled automatic opening of each service in its own dedicated web browser window/tab upon launch.
  - Implemented shell cleanup trap handlers (`EXIT`, `INT`, `TERM`) to gracefully terminate all background processes upon closing the terminal.
  - Removed the `Logs Reader` and `GitHub Repo` navigation buttons from the dashboard top navbar as requested.
  - Modernized FastAPI lifecycle handlers by migrating deprecated `@app.on_event("startup/shutdown")` to the official async `lifespan` context manager, resolving deprecation warnings.
- **Affected Files**:
  - `[MODIFIED]` `app.py`
  - `[MODIFIED]` `sync_github.command`
  - `[MODIFIED]` `sync_github.sh`
  - `[MODIFIED]` `run_ai_cctv.bat`
  - `[MODIFIED]` `logs.md`
- **Line Changes Breakdown**:
  - `app.py`: Lines 572–585 (Replaced `on_event` with `lifespan=lifespan`), Lines 1133–1137 (Removed navbar buttons).
  - `sync_github.command`: Lines 38–58 (Added background execution of `logs_reader.py`, shell trap handler, and independent browser openings).
  - `sync_github.sh`: Lines 38–58 (Added background execution of `logs_reader.py`, shell trap handler, and independent browser openings).
  - `run_ai_cctv.bat`: Lines 15–20 (Added background launch for `logs_reader.py`).
  - `logs.md`: Lines 140–175 (Added Log #004 entry).

---

### [Log #005] - SQLAlchemy Async ORM & SQLite WAL Database Architecture Integration
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 10:10:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Integrated enterprise-grade asynchronous database layer using **SQLAlchemy 2.0 Async ORM** and **SQLite with Write-Ahead Logging (WAL)**.
  - Implemented high-concurrency database pragmas (`PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`, `PRAGMA foreign_keys=ON;`) ensuring non-blocking reads and writes.
  - Created declarative database models (`models.py`) for Cameras (`CameraModel`), Zones (`ZoneModel`), Incidents (`IncidentModel`), and Audit Logs (`AuditLogModel`).
  - Built automatic database migration, schema initialization, and initial seeding routines from `settings.json` on startup (`database.py`).
  - Connected database persistence into `app.py` for real-time safety incident recording, supervisor review verification decisions (`verified` / `dismissed`), and zone polygon coordinates.
  - Updated `.gitignore` to exclude SQLite runtime database files (`*.db`, `*.db-wal`, `*.db-shm`).
- **Affected Files**:
  - `[ADDED]` `models.py`
  - `[ADDED]` `database.py`
  - `[MODIFIED]` `app.py`
  - `[MODIFIED]` `.gitignore`
  - `[MODIFIED]` `logs.md`
- **Line Changes Breakdown**:
  - `models.py`: Lines 1–135 (Defined CameraModel, ZoneModel, IncidentModel, and AuditLogModel).
  - `database.py`: Lines 1–185 (Created Async SQLAlchemy engine, SQLite WAL listener, session generator, and CRUD service).
  - `app.py`: Lines 95–150 (Integrated async incident saver), Lines 590–740 (Connected DB init to lifespan and updated incident/zone endpoints).
  - `.gitignore`: Lines 15–25 (Added ignore patterns for SQLite database files).
  - `logs.md`: Lines 165–200 (Added Log #005 entry).

---

### [Log #006] - Biometric Facial Recognition Engine, Employee Directory & Keyframe Track-Fusion
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 10:20:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Implemented real-time **Biometric Facial Recognition Engine** (`face_engine.py`) using OpenCV YuNet CNN face detector and SFace deep metric feature recognizer.
  - Built **Keyframe Track-Fusion Architecture**: ByteTrack body tracking is seamlessly fused with facial identity caching, locking recognized worker names onto track IDs without repetitive high-cost frame inference.
  - Added `EmployeeModel` and `AttendanceLogModel` to `models.py` with binary storage of 128-D L2-normalized biometric face embeddings.
  - Created asynchronous employee CRUD and in-memory vector roster matching in `database.py`.
  - Built complete **Employee Management Module & Enrollment Modal** in the Web Dashboard (`app.py`), supporting photo upload, real-time face landmark verification, and worker directory management.
  - Rendered recognized worker badges (` Name (Code) | Conf`) in bright gold/cyan directly on the live camera stream overlay.
- **Affected Files**:
  - `[ADDED]` `face_engine.py`
  - `[MODIFIED]` `models.py`
  - `[MODIFIED]` `database.py`
  - `[MODIFIED]` `app.py`
  - `[MODIFIED]` `logs.md`
- **Line Changes Breakdown**:
  - `face_engine.py`: Lines 1–115 (Created FaceEngine with YuNet alignment and SFace Cosine Similarity vector matching).
  - `models.py`: Lines 135–185 (Added EmployeeModel and AttendanceLogModel).
  - `database.py`: Lines 215–295 (Added db_get_employees, db_save_employee, db_delete_employee, db_load_all_face_embeddings).
  - `app.py`: Lines 340–495 (Integrated biometric recognition and track identity cache into AI loop), Lines 810–875 (Added Employee REST API), Lines 1300–1540 (Added Employees Modal UI and JS handlers).
  - `logs.md`: Lines 190–225 (Added Log #006 entry).

---

### [Log #007] - Logs Reader Multi-Line Markdown Parser & UI Card Scope Rendering Fix
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 10:25:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Resolved parser issue in `logs_reader.py` where nested multi-line markdown bullet points under `Objective / Purpose` and `Line Changes Breakdown` were stripped during text tokenization.
  - Upgraded `parse_logs_md()` to robustly extract multi-bullet objectives into structured `purpose_list` arrays, clean file tagging tokens, and detailed code scope descriptions.
  - Enhanced frontend card rendering in `logs_reader.py` to display purpose bullet lists (`<ul><li>`), clean file badges with status colors, and line-level changes with code formatting.
  - Verified 100% extraction accuracy across all changelog cards (Logs #001 through #007).
- **Affected Files**:
  - `[MODIFIED]` `logs_reader.py`
  - `[MODIFIED]` `logs.md`
- **Line Changes Breakdown**:
  - `logs_reader.py`: Lines 420–540 (Updated JavaScript UI rendering for purpose lists and diff cards), Lines 550–650 (Re-engineered Markdown AST tokenizer and line stripper).
  - `logs.md`: Lines 215–240 (Added Log #007 entry).

---

### [Log #008] - Non-Blocking Fast Socket Probe & OpenCV RTSP Timeout Suppression
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 10:40:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Eliminated repetitive 30-second OpenCV FFMPEG socket timeouts (`cap_ffmpeg_impl.hpp:453 Stream timeout triggered after 30000ms`) during offline or remote development.
  - Implemented ultra-fast non-blocking TCP socket pre-check (`is_nvr_online()`) probing `192.168.100.203:554` in under 5ms before initiating OpenCV `VideoCapture`.
  - Configured OpenCV log level suppression (`OPENCV_LOG_LEVEL=ERROR`, `cv2.setLogLevel`) to maintain a clean terminal output.
  - Enhanced simulation fallback to instantly engage high-tech synthetic feed when working away from the factory LAN.
- **Affected Files**:
  - `[MODIFIED]` `app.py`
  - `[MODIFIED]` `logs.md`
- **Line Changes Breakdown**:
  - `app.py`: Lines 15–30 (Added socket import and OpenCV log suppression), Lines 170–300 (Added is_nvr_online helper and modernized CameraStream capture loop).
  - `logs.md`: Lines 235–260 (Added Log #008 entry).

---

### [Log #009] - Complete Removal of Emojis & Clean Professional UI Standard
- **Author**: Ali Nasser
- **Timestamp**: 2026-08-22 10:45:00 UTC+3
- **AI Agent**: Antigravity
- **Objective / Purpose**:
  - Removed all emojis across the entire repository to establish a clean, professional, enterprise-grade engineering aesthetic.
  - Replaced UI icons, status indicators, and modal action tags in `app.py` and `logs_reader.py` with standard typography, CSS badges, and text labels.
  - Updated launcher scripts (`sync_github.command`, `sync_github.sh`) to use clean terminal status outputs ([OK], [WARNING]).
  - Cleaned all historical and active changelog card headers in `logs.md`.
- **Affected Files**:
  - `[MODIFIED]` `logs.md`
  - `[MODIFIED]` `logs_reader.py`
  - `[MODIFIED]` `app.py`
  - `[MODIFIED]` `sync_github.command`
  - `[MODIFIED]` `sync_github.sh`
- **Line Changes Breakdown**:
  - `logs.md`: Lines 1–260 (Stripped emoji prefixes from sections, headers, and metadata cards).
  - `logs_reader.py`: Lines 520–720 (Replaced emoji icons with clean badges and typography).
  - `app.py`: Lines 450–520, 1400–1650 (Cleaned alert messages, modal action buttons, and detection overlays).
  - `sync_github.command`: Lines 20–55 (Replaced terminal emojis with standard bracketed tags).
  - `sync_github.sh`: Lines 20–55 (Replaced terminal emojis with standard bracketed tags).

---
