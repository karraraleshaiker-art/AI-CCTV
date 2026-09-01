from cctv_ai.detector import supports_half_precision


def test_half_precision_is_disabled_for_cpu_device():
    assert not supports_half_precision("cpu")
