from __future__ import annotations

import argparse
import getpass
from urllib.parse import quote

import cv2

from cctv_ai.config import AppConfig, mask_camera_source, resolve_camera_source


TEMPLATES = {
    "hikvision": "/Streaming/Channels/{channel}{stream_code}",
    "dahua": "/cam/realmonitor?channel={channel}&subtype={subtype}",
    "generic": "/{stream}",
}


def build_url(args: argparse.Namespace) -> str:
    username = quote(args.username, safe="")
    password = quote(args.password or getpass.getpass("NVR password: "), safe="")

    if args.path:
        path = args.path if args.path.startswith("/") else f"/{args.path}"
    else:
        if args.template == "hikvision":
            stream_code = "01" if args.stream == "main" else "02"
            path = TEMPLATES["hikvision"].format(channel=args.channel, stream_code=stream_code)
        elif args.template == "dahua":
            subtype = "0" if args.stream == "main" else "1"
            path = TEMPLATES["dahua"].format(channel=args.channel, subtype=subtype)
        else:
            stream = args.main_stream if args.stream == "main" else args.sub_stream
            path = TEMPLATES["generic"].format(stream=stream)

    return f"rtsp://{username}:{password}@{args.host}:{args.port}{path}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe an NVR RTSP stream.")
    parser.add_argument("--config", default=None, help="Path to config.local.json. Uses the same input as the app.")
    parser.add_argument("--host", default="192.168.100.203")
    parser.add_argument("--port", default=554, type=int)
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default=None)
    parser.add_argument("--channel", default="14")
    parser.add_argument("--stream", choices=["main", "sub"], default="main")
    parser.add_argument("--template", choices=["hikvision", "dahua", "generic"], default="hikvision")
    parser.add_argument("--main-stream", default="0.1")
    parser.add_argument("--sub-stream", default="0.2")
    parser.add_argument("--path", default=None, help="Override the RTSP path, for example /Streaming/Channels/101.")
    args = parser.parse_args()

    if args.config:
        url = str(resolve_camera_source(AppConfig.from_file(args.config)))
    else:
        url = build_url(args)
    print(mask_camera_source(url))

    capture = cv2.VideoCapture(url, cv2.CAP_FFMPEG if url.lower().startswith("rtsp://") else 0)
    ok, frame = capture.read()
    capture.release()

    if not ok or frame is None:
        raise SystemExit("Could not read a frame from this RTSP stream.")

    print(f"Connected. First frame size: {frame.shape[1]}x{frame.shape[0]}")


def mask_password(url: str) -> str:
    if "@" not in url or ":" not in url.split("@", 1)[0]:
        return url
    prefix, suffix = url.split("@", 1)
    user_part, _ = prefix.rsplit(":", 1)
    return f"{user_part}:****@{suffix}"


if __name__ == "__main__":
    main()
