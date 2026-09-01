from cctv_ai.detections import BBox, Detection
import numpy as np

from cctv_ai.pipeline import is_flat_frame, is_phone_near_person, normalized_jpeg_quality
from cctv_ai.tracker import Track


def test_phone_inside_person_upper_body_counts_as_near():
    track = Track(id=1, bbox=BBox(100, 100, 220, 420), confidence=0.9)
    phone = Detection(label="cell phone", confidence=0.8, bbox=BBox(150, 175, 170, 205))

    assert is_phone_near_person(phone, track)


def test_phone_far_from_person_does_not_count_as_near():
    track = Track(id=1, bbox=BBox(100, 100, 220, 420), confidence=0.9)
    phone = Detection(label="cell phone", confidence=0.8, bbox=BBox(500, 500, 530, 540))

    assert not is_phone_near_person(phone, track)


def test_jpeg_quality_is_clamped_to_reasonable_range():
    assert normalized_jpeg_quality(10) == 35
    assert normalized_jpeg_quality(70) == 70
    assert normalized_jpeg_quality(100) == 95


def test_flat_frame_detection_flags_uniform_gray_frame():
    frame = np.full((20, 20, 3), 128, dtype=np.uint8)

    assert is_flat_frame(frame, 4.0)
