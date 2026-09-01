from cctv_ai.alerts import AlertStore


def test_alert_store_persists_alert_history(tmp_path):
    history_path = tmp_path / "alerts.jsonl"
    evidence_path = tmp_path / "evidence.jpg"
    store = AlertStore(cooldown_seconds=0, history_path=history_path)

    alert = store.add("phone_use", 7, "Person #7 appears to be using a phone.", evidence_path=evidence_path)

    assert alert is not None
    reloaded = AlertStore(cooldown_seconds=0, history_path=history_path)
    alerts = reloaded.recent()
    assert alerts[0]["id"] == alert.id
    assert alerts[0]["evidence_path"] == str(evidence_path)
    assert alerts[0]["acknowledged"] is False


def test_alert_store_acknowledges_persisted_alert(tmp_path):
    history_path = tmp_path / "alerts.jsonl"
    store = AlertStore(cooldown_seconds=0, history_path=history_path)
    alert = store.add("left_zone", 4, "Person #4 left the assigned place.")

    assert alert is not None
    assert store.acknowledge(alert.id)

    reloaded = AlertStore(cooldown_seconds=0, history_path=history_path)
    assert reloaded.recent()[0]["acknowledged"] is True
