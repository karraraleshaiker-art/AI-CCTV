from cctv_ai.detections import BBox, Detection
from cctv_ai.pipeline import is_phone_near_person
from cctv_ai.tracker import Track


def test_phone_inside_person_upper_body_counts_as_near():
    track = Track(id=1, bbox=BBox(100, 100, 220, 420), confidence=0.9)
    phone = Detection(label="cell phone", confidence=0.8, bbox=BBox(150, 175, 170, 205))

    assert is_phone_near_person(phone, track)


def test_phone_far_from_person_does_not_count_as_near():
    track = Track(id=1, bbox=BBox(100, 100, 220, 420), confidence=0.9)
    phone = Detection(label="cell phone", confidence=0.8, bbox=BBox(500, 500, 530, 540))

    assert not is_phone_near_person(phone, track)

