from __future__ import annotations

from dataclasses import dataclass

from .detections import BBox, Detection


@dataclass(slots=True)
class Track:
    id: int
    bbox: BBox
    confidence: float
    age: int = 0
    missed: int = 0
    inside_zone_frames: int = 0
    outside_zone_frames: int = 0
    was_confirmed_inside_zone: bool = False
    phone_frames: int = 0


class PersonTracker:
    def __init__(self, max_missed: int = 20, min_iou: float = 0.2) -> None:
        self.max_missed = max_missed
        self.min_iou = min_iou
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    @property
    def tracks(self) -> list[Track]:
        return list(self._tracks.values())

    def update(self, detections: list[Detection]) -> list[Track]:
        unmatched_track_ids = set(self._tracks.keys())
        unmatched_detections = set(range(len(detections)))
        matches: list[tuple[int, int]] = []

        candidates: list[tuple[float, int, int]] = []
        for track_id, track in self._tracks.items():
            for index, detection in enumerate(detections):
                score = track.bbox.iou(detection.bbox)
                if score >= self.min_iou:
                    candidates.append((score, track_id, index))

        for _, track_id, index in sorted(candidates, reverse=True):
            if track_id not in unmatched_track_ids or index not in unmatched_detections:
                continue
            matches.append((track_id, index))
            unmatched_track_ids.remove(track_id)
            unmatched_detections.remove(index)

        for track_id, index in matches:
            detection = detections[index]
            track = self._tracks[track_id]
            track.bbox = detection.bbox
            track.confidence = detection.confidence
            track.age += 1
            track.missed = 0

        for track_id in unmatched_track_ids:
            track = self._tracks[track_id]
            track.age += 1
            track.missed += 1

        for index in unmatched_detections:
            detection = detections[index]
            self._tracks[self._next_id] = Track(
                id=self._next_id,
                bbox=detection.bbox,
                confidence=detection.confidence,
            )
            self._next_id += 1

        expired = [track_id for track_id, track in self._tracks.items() if track.missed > self.max_missed]
        for track_id in expired:
            del self._tracks[track_id]

        return self.tracks

