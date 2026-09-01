from __future__ import annotations

from dataclasses import dataclass


Point = tuple[float, float]


@dataclass(slots=True)
class Zone:
    points: list[Point]

    def contains(self, point: Point) -> bool:
        if len(self.points) < 3:
            return False

        x, y = point
        inside = False
        j = len(self.points) - 1
        for i, current in enumerate(self.points):
            xi, yi = current
            xj, yj = self.points[j]
            crosses = (yi > y) != (yj > y)
            if crosses:
                x_at_y = (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
                if x < x_at_y:
                    inside = not inside
            j = i
        return inside

    def to_pixels(self, width: int, height: int) -> "Zone":
        return Zone([(x * width, y * height) for x, y in self.points])

    def to_normalized(self, width: int, height: int) -> "Zone":
        if width <= 0 or height <= 0:
            return Zone([])
        return Zone([(x / width, y / height) for x, y in self.points])

    def sanitized(self) -> "Zone":
        return Zone([(clamp(x), clamp(y)) for x, y in self.points])


def clamp(value: float) -> float:
    return min(1.0, max(0.0, float(value)))

