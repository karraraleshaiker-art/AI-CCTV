from cctv_ai.config import AppConfig, build_rtsp_path, display_camera_source, resolve_camera_source


def test_default_config_resolves_to_nvr_rtsp_source():
    config = AppConfig(nvr_password="secret")

    assert resolve_camera_source(config) == "rtsp://admin:secret@192.168.100.203:554/Streaming/Channels/1401"


def test_explicit_camera_source_still_allows_test_video_or_webcam():
    config = AppConfig(camera_source="0")

    assert resolve_camera_source(config) == 0


def test_nvr_substream_builds_hikvision_channel_path():
    assert build_rtsp_path("2", "sub", "hikvision") == "/Streaming/Channels/202"


def test_display_camera_source_uses_resolved_rtsp_url():
    config = AppConfig(nvr_username="operator", nvr_password="pw", nvr_channel="3")

    assert display_camera_source(config) == "rtsp://operator:pw@192.168.100.203:554/Streaming/Channels/301"


def test_default_config_uses_high_quality_processing_profile():
    config = AppConfig()

    assert config.confidence == 0.25
    assert config.model_imgsz == 960
    assert config.stream_fps == 20
    assert config.frame_width == 1280
    assert config.jpeg_quality == 85
    assert config.rtsp_stale_frame_grabs == 0
    assert config.tracker_max_missed == 60
