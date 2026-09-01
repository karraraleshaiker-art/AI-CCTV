from __future__ import annotations

import json
import re
import shutil
import socket
import sys
import zipfile
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RTSP_CREDENTIAL_RE = re.compile(r"(rtsp://[^:\s/@]+:)([^@\s]+)(@)", re.IGNORECASE)


def main() -> None:
    zip_path = collect_diagnostics()
    print(zip_path)


def collect_diagnostics() -> Path:
    diagnostics_dir = PROJECT_ROOT / "diagnostics"
    diagnostics_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    package_dir = diagnostics_dir / f"ai-cctv-diagnostics-{stamp}"
    package_dir.mkdir()

    write_manifest(package_dir)
    copy_text_if_exists(PROJECT_ROOT / "runtime_launcher.log", package_dir / "runtime_launcher.log")
    copy_text_tree(PROJECT_ROOT / "runtime_logs", package_dir / "runtime_logs")
    copy_text_if_exists(PROJECT_ROOT / "runtime_state.json", package_dir / "runtime_state.json")
    copy_text_if_exists(PROJECT_ROOT / "config.example.json", package_dir / "config.example.json")
    copy_text_if_exists(PROJECT_ROOT / "config.nvr.example.json", package_dir / "config.nvr.example.json")

    zip_path = diagnostics_dir / f"{package_dir.name}.zip"
    zip_directory(package_dir, zip_path)
    shutil.rmtree(package_dir)
    return zip_path


def write_manifest(package_dir: Path) -> None:
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "included": [
            "runtime_launcher.log",
            "runtime_logs/",
            "runtime_state.json",
            "config.example.json",
            "config.nvr.example.json",
        ],
        "excluded": [
            "config.local.json",
            "NVR password",
            ".venv/",
            "yolov8n.pt",
            "output/",
        ],
        "note": "Text files are sanitized before packaging. RTSP passwords are replaced with ****.",
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def copy_text_tree(source_dir: Path, target_dir: Path) -> None:
    if not source_dir.exists():
        return
    for source in source_dir.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_dir)
        copy_text_if_exists(source, target_dir / relative)


def copy_text_if_exists(source: Path, target: Path) -> None:
    if not source.exists() or not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8", errors="replace")
    target.write_text(sanitize_text(text), encoding="utf-8")


def sanitize_text(text: str) -> str:
    return RTSP_CREDENTIAL_RE.sub(r"\1****\3", text)


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(source_dir.rglob("*")):
            if source.is_file():
                archive.write(source, source.relative_to(source_dir))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Could not collect diagnostics: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
