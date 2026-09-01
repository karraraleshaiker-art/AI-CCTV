from cctv_ai.app import mask_camera_source, tail_text, with_evidence_urls


def test_mask_camera_source_hides_rtsp_password():
    source = "rtsp://admin:secret@192.168.100.203:554/0.1"

    assert mask_camera_source(source) == "rtsp://admin:****@192.168.100.203:554/0.1"


def test_mask_camera_source_keeps_non_url_source():
    assert mask_camera_source("0") == "0"


def test_with_evidence_urls_uses_evidence_filename_only():
    alerts = [{"evidence_path": "output/evidence/example.jpg"}]

    assert with_evidence_urls(alerts)[0]["evidence_url"] == "/evidence/example.jpg"


def test_tail_text_returns_requested_line_count(tmp_path):
    path = tmp_path / "app.log"
    path.write_text("one\ntwo\nthree\n", encoding="utf-8")

    assert tail_text(path, 2) == "two\nthree"
