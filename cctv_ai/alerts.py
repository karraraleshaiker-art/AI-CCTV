from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from threading import Lock
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Alert:
    id: str
    kind: str
    track_id: int
    message: str
    timestamp: float
    evidence_path: str | None = None
    acknowledged: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["iso_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        return data


class AlertStore:
    def __init__(self, cooldown_seconds: float, history_path: str | Path | None = None, max_events: int = 200) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.history_path = Path(history_path) if history_path else None
        self._events: deque[Alert] = deque(maxlen=max_events)
        self._last_by_key: dict[tuple[str, int], float] = {}
        self._lock = Lock()
        self._load()

    def add(self, kind: str, track_id: int, message: str, evidence_path: str | Path | None = None) -> Alert | None:
        now = time.time()
        key = (kind, track_id)
        with self._lock:
            last = self._last_by_key.get(key, 0.0)
            if now - last < self.cooldown_seconds:
                return None
            alert = Alert(
                id=uuid4().hex,
                kind=kind,
                track_id=track_id,
                message=message,
                timestamp=now,
                evidence_path=str(evidence_path) if evidence_path else None,
            )
            self._events.appendleft(alert)
            self._last_by_key[key] = now
            self._save_locked()
            return alert

    def recent(self, limit: int = 50) -> list[dict[str, object]]:
        with self._lock:
            return [event.as_dict() for event in list(self._events)[:limit]]

    def acknowledge(self, alert_id: str) -> bool:
        with self._lock:
            updated = False
            alerts: list[Alert] = []
            for alert in self._events:
                if alert.id == alert_id:
                    alerts.append(replace(alert, acknowledged=True))
                    updated = True
                else:
                    alerts.append(alert)
            if not updated:
                return False
            self._events = deque(alerts, maxlen=self._events.maxlen)
            self._save_locked()
            return True

    def _load(self) -> None:
        if self.history_path is None or not self.history_path.exists():
            return

        loaded: list[Alert] = []
        for line in self.history_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                loaded.append(
                    Alert(
                        id=str(data.get("id") or uuid4().hex),
                        kind=str(data["kind"]),
                        track_id=int(data["track_id"]),
                        message=str(data["message"]),
                        timestamp=float(data["timestamp"]),
                        evidence_path=data.get("evidence_path"),
                        acknowledged=bool(data.get("acknowledged", False)),
                    )
                )
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue

        for alert in loaded[-self._events.maxlen :]:
            self._events.appendleft(alert)
            self._last_by_key[(alert.kind, alert.track_id)] = alert.timestamp

    def _save_locked(self) -> None:
        if self.history_path is None:
            return
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        events = list(reversed(self._events))
        payload = "\n".join(json.dumps(event.as_dict(), separators=(",", ":")) for event in events)
        self.history_path.write_text(payload + ("\n" if payload else ""), encoding="utf-8")
