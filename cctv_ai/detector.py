from __future__ import annotations

from collections.abc import Iterable

from .detections import BBox, Detection


class DetectorError(RuntimeError):
    pass


class YoloDetector:
    """Small wrapper around Ultralytics YOLO."""

    def __init__(
        self,
        model_name: str,
        confidence: float,
        iou_threshold: float,
        imgsz: int,
        device: str | None = None,
        half: bool = True,
    ) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise DetectorError(
                "Missing dependency 'ultralytics'. Install requirements with "
                "`pip install -r requirements.txt`."
            ) from exc

        self.model = YOLO(model_name)
        self.confidence = confidence
        self.iou_threshold = iou_threshold
        self.imgsz = imgsz
        self.device = device
        self.half = half and supports_half_precision(device)

    def detect(self, frame) -> list[Detection]:
        results = self.model(
            frame,
            conf=self.confidence,
            iou=self.iou_threshold,
            verbose=False,
            classes=[0, 67],
            imgsz=self.imgsz,
            device=self.device,
            half=self.half,
        )
        detections: list[Detection] = []

        for result in results:
            names = result.names
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                label = str(names.get(cls_id, cls_id))
                if label not in {"person", "cell phone"}:
                    continue
                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
                detections.append(Detection(label=label, confidence=confidence, bbox=BBox(x1, y1, x2, y2)))

        return detections


def split_detections(detections: Iterable[Detection]) -> tuple[list[Detection], list[Detection]]:
    people: list[Detection] = []
    phones: list[Detection] = []
    for detection in detections:
        if detection.label == "person":
            people.append(detection)
        elif detection.label == "cell phone":
            phones.append(detection)
    return people, phones


def supports_half_precision(device: str | None) -> bool:
    if device and device.lower() == "cpu":
        return False
    try:
        import torch
    except ImportError:
        return False
    return bool(torch.cuda.is_available())
