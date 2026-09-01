from __future__ import annotations

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True, slots=True)
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def iou(self, other: "BBox") -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        union = self.area + other.area - intersection
        if union <= 0:
            return 0.0
        return intersection / union

    def contains_point(self, point: tuple[float, float]) -> bool:
        x, y = point
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def distance_to(self, other: "BBox") -> float:
        ax, ay = self.center
        bx, by = other.center
        return hypot(ax - bx, ay - by)

    def upper_region(self) -> "BBox":
        return BBox(self.x1, self.y1, self.x2, self.y1 + self.height * 0.65)

    def expanded(self, ratio: float) -> "BBox":
        pad_x = self.width * ratio
        pad_y = self.height * ratio
        return BBox(self.x1 - pad_x, self.y1 - pad_y, self.x2 + pad_x, self.y2 + pad_y)

    def as_int_tuple(self) -> tuple[int, int, int, int]:
        return (int(self.x1), int(self.y1), int(self.x2), int(self.y2))


@dataclass(frozen=True, slots=True)
class Detection:
    label: str
    confidence: float
    bbox: BBox

