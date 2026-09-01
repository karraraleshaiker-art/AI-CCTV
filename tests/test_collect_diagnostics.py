from tools.collect_diagnostics import sanitize_text


def test_sanitize_text_redacts_rtsp_password():
    text = "Opening rtsp://admin:secret123@192.168.100.203:554/Streaming/Channels/1401"

    assert sanitize_text(text) == "Opening rtsp://admin:****@192.168.100.203:554/Streaming/Channels/1401"


def test_sanitize_text_leaves_url_without_password():
    text = "Opening rtsp://192.168.100.203:554/Streaming/Channels/1401"

    assert sanitize_text(text) == text
