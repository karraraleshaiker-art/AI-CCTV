from tools.run_nvr import build_auto_candidates, build_rtsp_path


def test_hikvision_channel_stream_path():
    assert build_rtsp_path("2", "sub", "hikvision") == "/Streaming/Channels/202"


def test_generic_stream_path_uses_0_dot_1_and_0_dot_2():
    assert build_rtsp_path("1", "main", "generic") == "/0.1"
    assert build_rtsp_path("1", "sub", "generic") == "/0.2"


def test_auto_candidates_include_common_formats():
    candidates = dict(build_auto_candidates("1", "main"))

    assert candidates["generic stream"] == "/0.1"
    assert candidates["hikvision"] == "/Streaming/Channels/101"
    assert candidates["dahua"] == "/cam/realmonitor?channel=1&subtype=0"


def test_auto_candidates_prefer_channel_specific_paths_for_channel_two():
    labels = [label for label, _ in build_auto_candidates("2", "main")]

    assert labels[0] != "generic stream"
