from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from .zones import Zone


class RuntimeState:
    def __init__(self, path: str | Path, initial_zone: list[tuple[float, float]]) -> None:
        self.path = Path(path)
        self._lock = Lock()
        self._zone = Zone(initial_zone).sanitized()
        self._load()

    @property
    def zone(self) -> Zone:
        with self._lock:
            return Zone(list(self._zone.points))

    def set_zone(self, points: list[tuple[float, float]]) -> Zone:
        zone = Zone(points).sanitized()
        if len(zone.points) < 3:
            raise ValueError("Zone must contain at least three points.")
        with self._lock:
            self._zone = zone
            self._save_locked()
            return Zone(list(self._zone.points))

    def as_dict(self) -> dict[str, object]:
        with self._lock:
            return self._as_dict_locked()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        zone = data.get("zone")
        if isinstance(zone, list) and len(zone) >= 3:
            self._zone = Zone([tuple(point) for point in zone]).sanitized()

    def _save_locked(self) -> None:
        self.path.write_text(json.dumps(self._as_dict_locked(), indent=2), encoding="utf-8")

    def _as_dict_locked(self) -> dict[str, object]:
        return {"zone": self._zone.points}
