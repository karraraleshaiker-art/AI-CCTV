from __future__ import annotations

import getpass
import os
import socket
import sys
import threading
import webbrowser
from dataclasses import replace
from pathlib import Path

import uvicorn

from cctv_ai.app import create_app
from cctv_ai.config import AppConfig, build_rtsp_path, build_rtsp_url as build_config_rtsp_url
from cctv_ai.logging_utils import configure_logging
from tools.rtsp_probe import mask_password


DEFAULT_HOST = "192.168.100.203"
DEFAULT_PORT = 554
DEFAULT_CHANNEL = "14"
DEFAULT_STREAM = "main"
DEFAULT_URL_STYLE = "hikvision"
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 8000


def main() -> None:
    install_output_log()
    print("Using saved NVR settings:")
    print(f"  NVR IP: {DEFAULT_HOST}")
    print(f"  RTSP port: {DEFAULT_PORT}")
    print(f"  Channel: {DEFAULT_CHANNEL}")
    print(f"  Stream: {DEFAULT_STREAM}")
    print(f"  RTSP style: {DEFAULT_URL_STYLE}")
    print("Only the NVR login is required. The password is not saved.\n")

    nvr_host = DEFAULT_HOST
    if not port_is_free(nvr_host, DEFAULT_PORT):
        print(f"Network check passed: {nvr_host}:{DEFAULT_PORT} is reachable.")
    else:
        print(f"\nCannot reach RTSP port {DEFAULT_PORT} on {nvr_host}.")
        print("Check that the NVR IP is correct, your PC is on the same network, and RTSP is enabled on the NVR.")
        raise SystemExit(1)

    username = prompt_default("NVR username", "admin")
    password = getpass.getpass("NVR password: ")

    camera_source = build_rtsp_url(nvr_host, username, password, DEFAULT_CHANNEL, DEFAULT_STREAM, DEFAULT_URL_STYLE)
    config = replace(AppConfig(), camera_source=camera_source)
    log_file = configure_logging(config.log_dir)
    native_log_file = redirect_native_stderr(Path(config.log_dir) / "native_stderr.log")

    dashboard_url = f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}"
    print("\nUsing camera:")
    print(mask_password(camera_source))
    print(f"Runtime log: {log_file}")
    print(f"Native decoder log: {native_log_file}")
    print(f"\nOpening dashboard: {dashboard_url}")
    print("If the browser does not open, paste that address into Chrome or Edge.")
    print("Leave this window open. Press CTRL+C to stop.\n")

    threading.Timer(3.0, lambda: webbrowser.open(dashboard_url)).start()
    uvicorn.run(create_app(config), host=DASHBOARD_HOST, port=DASHBOARD_PORT)


def prompt_default(label: str, default: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def install_output_log() -> None:
    log_path = Path("runtime_launcher.log")
    log_file = log_path.open("w", encoding="utf-8")
    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)
    print(f"Writing launcher log to: {log_path.resolve()}\n")


def redirect_native_stderr(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    os.dup2(fd, 2)
    os.close(fd)
    return path


class Tee:
    def __init__(self, *streams) -> None:
        self.streams = streams

    def write(self, data: str) -> int:
        for stream in self.streams:
            stream.write(data)
            stream.flush()
        return len(data)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()

    def isatty(self) -> bool:
        return any(getattr(stream, "isatty", lambda: False)() for stream in self.streams)


def prompt_choice(
    label: str,
    choices: dict[str, str],
    default: str,
    lines: list[str] | None = None,
) -> str:
    if lines:
        print(label + ":")
        for line in lines:
            print("  " + line)
    value = input(f"{label} [{default}]: ").strip().lower()
    if not value:
        return default
    while value not in choices:
        print("Please choose one of: " + ", ".join(choices))
        value = input(f"{label} [{default}]: ").strip().lower()
        if not value:
            return default
    return choices[value]


def build_rtsp_url(
    host: str,
    username: str,
    password: str,
    channel: str,
    stream: str,
    url_style: str,
) -> str:
    if url_style == "manual":
        path = input("RTSP path, for example /Streaming/Channels/101: ").strip()
        return build_rtsp_url_from_path(host, username, password, path)
    return build_config_rtsp_url(host, DEFAULT_PORT, username, password, channel, stream, url_style)


def build_rtsp_url_from_path(host: str, username: str, password: str, path: str) -> str:
    return build_config_rtsp_url(host, DEFAULT_PORT, username, password, "1", "main", "hikvision", path=path)


def build_auto_candidates(channel: str, stream: str) -> list[tuple[str, str]]:
    stream_name = "0.1" if stream == "main" else "0.2"
    hikvision_code = "01" if stream == "main" else "02"
    dahua_subtype = "0" if stream == "main" else "1"
    channel_candidates = [
        ("generic channel/stream", f"/{channel}/{stream_name}"),
        ("generic channel name", f"/channel{channel}/{stream_name}"),
        ("generic short channel name", f"/ch{channel}/{stream_name}"),
        ("hikvision", f"/Streaming/Channels/{channel}{hikvision_code}"),
        ("dahua", f"/cam/realmonitor?channel={channel}&subtype={dahua_subtype}"),
    ]
    plain_stream = [("generic stream", f"/{stream_name}")]
    if channel in {"", "1"}:
        return plain_stream + channel_candidates
    return channel_candidates + plain_stream


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) != 0


if __name__ == "__main__":
    try:
        if not port_is_free(DASHBOARD_HOST, DASHBOARD_PORT):
            print(f"Port {DASHBOARD_PORT} is already in use. Close the old AI CCTV window first.")
            raise SystemExit(1)
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        raise SystemExit(0)
    except Exception as exc:
        print(f"\nCould not start the AI CCTV system: {exc}")
        raise SystemExit(1) from exc
