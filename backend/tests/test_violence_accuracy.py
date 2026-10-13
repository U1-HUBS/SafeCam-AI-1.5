import time
import pytest
import numpy as np
import cv2

from backend.services.ai_service import (
    KineticMotionEstimator,
    TemporalAggregator,
    ViolenceClassifier,
    get_best_torch_device
)

def test_device_selection():
    device = get_best_torch_device()
    assert device in ["cuda", "cpu"]

    classifier_cpu = ViolenceClassifier(use_gpu=False)
    assert classifier_cpu.device == "cpu"

def test_kinetic_motion_static_scene():
    estimator = KineticMotionEstimator()
    static_frame = np.full((240, 320, 3), 128, dtype=np.uint8)
    t = time.time()

    # Frame 1: baseline
    energy1, turb1, active1 = estimator.update(static_frame, t)
    assert not active1

    # Frame 2: identical static frame
    energy2, turb2, active2 = estimator.update(static_frame, t + 0.5)
    assert energy2 == 0.0
    assert not active2

def test_kinetic_motion_chaotic_movement():
    estimator = KineticMotionEstimator()
    t = time.time()

    # Frame 1: two people standing
    frame1 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(frame1, (140, 120), 25, (30, 30, 200), -1)
    cv2.circle(frame1, (180, 120), 25, (200, 30, 30), -1)
    estimator.update(frame1, t)

    # Frame 2: rapid physical struggle (large displacement + high contrast movement)
    frame2 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(frame2, (160, 140), 30, (30, 30, 220), -1)
    cv2.circle(frame2, (150, 100), 30, (220, 30, 30), -1)
    cv2.line(frame2, (130, 110), (180, 130), (255, 255, 255), 5)

    energy, turb, is_active = estimator.update(frame2, t + 0.5)
    assert is_active is True
    assert energy > 0.02
    assert turb > 0.10

def test_ema_smoothing_suppresses_transient_noise():
    agg = TemporalAggregator(
        camera_id=1,
        window_seconds=6.0,
        positive_ratio=0.5,
        min_positive_frames=3,
        threshold=0.30,
        ema_alpha=0.40
    )
    t = time.time()

    # Isolated spike frame (e.g. glitch, camera artifact, quick gesture)
    res = agg.add_prediction(t, "a physical fight", "Suspected Fight", 0.90, True)
    assert res is None, "A single isolated high-confidence spike must be suppressed by EMA and duration filter"

    # Followed by calm frames
    res2 = agg.add_prediction(t + 0.5, "students walking", "Non-Violent", 0.10, False)
    assert res2 is None
    res3 = agg.add_prediction(t + 1.0, "students walking", "Non-Violent", 0.10, False)
    assert res3 is None
    assert agg.ema_confidence < 0.40

def test_sustained_violence_triggers_alert():
    agg = TemporalAggregator(
        camera_id=2,
        window_seconds=6.0,
        positive_ratio=0.5,
        min_positive_frames=3,
        threshold=0.25,
        ema_alpha=0.40
    )
    t = time.time()

    # Sustained frames
    agg.add_prediction(t, "a physical fight", "Suspected Fight", 0.70, True)
    agg.add_prediction(t + 0.5, "a physical fight", "Suspected Fight", 0.75, True)
    trigger = agg.add_prediction(t + 1.0, "a physical fight", "Suspected Fight", 0.80, True)

    assert trigger is not None
    assert trigger["camera_id"] == 2
    assert trigger["category"] == "Suspected Fight"
    assert trigger["peak_confidence"] == pytest.approx(0.80)
    assert "ema_confidence" in trigger

def test_smooth_uniform_walking_not_flagged_as_violent():
    classifier = ViolenceClassifier(use_gpu=False)
    t = time.time()

    # Create synthetic hallway background
    bg = np.full((240, 320, 3), 150, dtype=np.uint8)

    # Frame 1: walking person at pos x=50
    f1 = bg.copy()
    cv2.circle(f1, (50, 120), 15, (50, 50, 50), -1)
    label1, cat1, conf1, is_violent1 = classifier.predict_frame(f1, t)
    assert not is_violent1

    # Frame 2: walking person moved smoothly to pos x=60
    f2 = bg.copy()
    cv2.circle(f2, (60, 120), 15, (50, 50, 50), -1)
    label2, cat2, conf2, is_violent2 = classifier.predict_frame(f2, t + 0.5)

    # Smooth non-turbulent walking must not be classified as violence
    assert not is_violent2
    assert conf2 < 0.35

def test_solo_shadowboxing_suppression():
    classifier = ViolenceClassifier(use_gpu=False)
    estimator = KineticMotionEstimator()
    t = time.time()

    # Frame 1: Single person in center of room
    f1 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f1, (160, 100), 20, (30, 200, 30), -1)
    estimator.update(f1, t)

    # Frame 2: Rapid punch motion (rapid limb displacement by single actor)
    f2 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f2, (160, 100), 20, (30, 200, 30), -1)
    cv2.line(f2, (160, 100), (220, 90), (255, 255, 255), 8) # extended arm/punch

    label, cat, conf, is_violent = classifier.predict_frame(
        f2,
        timestamp=t + 0.1,
        motion_estimator=estimator,
        override_bodies=[(130, 60, 60, 140)] # Exactly 1 person
    )

    assert not is_violent, "Solo shadowboxing must be suppressed"
    assert cat == "Non-Violent"
    assert "single person" in label

def test_solo_kicking_suppression():
    classifier = ViolenceClassifier(use_gpu=False)
    estimator = KineticMotionEstimator()
    t = time.time()

    f1 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f1, (160, 100), 20, (30, 200, 30), -1)
    estimator.update(f1, t)

    # Rapid high kick motion by solitary actor
    f2 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f2, (160, 100), 20, (30, 200, 30), -1)
    cv2.line(f2, (160, 150), (230, 130), (255, 255, 255), 8) # extended leg/kick

    label, cat, conf, is_violent = classifier.predict_frame(
        f2,
        timestamp=t + 0.1,
        motion_estimator=estimator,
        override_bodies=[(130, 60, 60, 140)] # Exactly 1 person
    )

    assert not is_violent, "Solo martial arts kicking must be suppressed"
    assert cat == "Non-Violent"

def test_two_people_non_contact_suppression():
    classifier = ViolenceClassifier(use_gpu=False)
    estimator = KineticMotionEstimator()
    t = time.time()

    # Two people standing at a distance: Person 1 at x=40, Person 2 at x=220
    b1 = (30, 50, 50, 130)
    b2 = (210, 50, 50, 130)

    f1 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f1, (50, 90), 20, (30, 200, 30), -1)
    cv2.circle(f1, (230, 90), 20, (200, 30, 30), -1)
    estimator.update(f1, t)

    # Person 1 shadowboxes/punches in air towards x=100 (stops far before Person 2 at x=210)
    f2 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f2, (50, 90), 20, (30, 200, 30), -1)
    cv2.circle(f2, (230, 90), 20, (200, 30, 30), -1)
    cv2.line(f2, (50, 90), (105, 90), (255, 255, 255), 8)

    label, cat, conf, is_violent = classifier.predict_frame(
        f2,
        timestamp=t + 0.1,
        motion_estimator=estimator,
        override_bodies=[b1, b2]
    )

    assert not is_violent, "Non-contact shadowboxing between people must be suppressed"
    assert cat == "Non-Violent"
    assert "without physical contact" in label

def test_two_people_hand_contact_detected():
    classifier = ViolenceClassifier(use_gpu=False)
    estimator = KineticMotionEstimator()
    t = time.time()

    # Person 1 at x=50, Person 2 close by at x=130
    b1 = (40, 50, 50, 130)
    b2 = (120, 50, 50, 130)

    f1 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f1, (60, 90), 20, (30, 200, 30), -1)
    cv2.circle(f1, (140, 90), 20, (200, 30, 30), -1)
    estimator.update(f1, t)

    # Violent hand strike that connects into Person 2's body box (x reaches 135)
    f2 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f2, (60, 90), 20, (30, 200, 30), -1)
    cv2.circle(f2, (140, 90), 20, (200, 30, 30), -1)
    cv2.line(f2, (60, 80), (135, 80), (255, 255, 255), 10) # punch connects

    label, cat, conf, is_violent = classifier.predict_frame(
        f2,
        timestamp=t + 0.1,
        motion_estimator=estimator,
        override_bodies=[b1, b2]
    )

    assert is_violent is True, "Physical punch contact with high turbulence must trigger alert"
    assert cat == "Suspected Fight"
    assert "punch" in label or "strike" in label or "fight" in label

def test_two_people_foot_contact_detected():
    classifier = ViolenceClassifier(use_gpu=False)
    estimator = KineticMotionEstimator()
    t = time.time()

    # Person 1 at x=50, Person 2 close by at x=130
    b1 = (40, 50, 50, 130)
    b2 = (120, 50, 50, 130)

    f1 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f1, (60, 90), 20, (30, 200, 30), -1)
    cv2.circle(f1, (140, 90), 20, (200, 30, 30), -1)
    estimator.update(f1, t)

    # Violent kick strike that connects into Person 2's body box (foot at y=150, x reaches 135)
    f2 = np.full((240, 320, 3), 100, dtype=np.uint8)
    cv2.circle(f2, (60, 90), 20, (30, 200, 30), -1)
    cv2.circle(f2, (140, 90), 20, (200, 30, 30), -1)
    cv2.line(f2, (60, 150), (135, 140), (255, 255, 255), 10) # kick connects

    label, cat, conf, is_violent = classifier.predict_frame(
        f2,
        timestamp=t + 0.1,
        motion_estimator=estimator,
        override_bodies=[b1, b2]
    )

    assert is_violent is True, "Physical kick contact with high turbulence must trigger alert"
    assert cat == "Suspected Fight"
    assert "kick" in label or "strike" in label or "fight" in label


def test_yolo_person_detector_loads_and_handles_frames():
    from backend.services.ai_service import YoloPersonDetector
    detector = YoloPersonDetector()
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    persons = detector.detect_persons(frame)
    assert isinstance(persons, list)


def test_yolo_merges_overlapping_bounding_boxes():
    from backend.services.ai_service import YoloPersonDetector
    detector = YoloPersonDetector()

    # Two heavily overlapping candidate boxes for the same single person
    box1 = (50, 40, 60, 120)
    box2 = (55, 45, 55, 115)
    merged = detector._merge_overlapping_boxes([box1, box2], [0.90, 0.85], iou_thresh=0.35)

    assert len(merged) == 1, "Candidate boxes for the same person must be merged into 1 person"
    assert merged[0][1] == 0.90


def test_camera_worker_renders_annotated_frame_with_yolo_labels():
    from backend.services.stream_manager import CameraStreamWorker
    worker = CameraStreamWorker(
        camera_id=99,
        stream_url="test.mp4",
        is_simulation=True,
        ai_enabled=True
    )
    frame = np.full((240, 320, 3), 120, dtype=np.uint8)
    persons = [{"id": 1, "box": (50, 40, 60, 120), "conf": 0.92, "label": "Person #1"}]

    worker._render_annotated_frame(frame, persons, is_violent=False, label="single person exercising alone")
    assert worker.latest_annotated_frame is not None
    assert worker.latest_annotated_frame.shape == frame.shape
    # Ensure drawing changed pixels from uniform background
    assert not np.array_equal(worker.latest_annotated_frame, frame)


def test_stream_manager_annotated_toggle():
    from backend.services.stream_manager import StreamManager
    sm = StreamManager()
    worker = sm.workers.get(1)
    # Simulate a worker
    from backend.services.stream_manager import CameraStreamWorker
    w = CameraStreamWorker(camera_id=1, stream_url="fake.mp4", is_simulation=True)
    f = np.full((240, 320, 3), 100, dtype=np.uint8)
    w.latest_frame = f
    w.latest_persons = [{"id": 1, "box": (40, 40, 50, 100), "conf": 0.90, "label": "Person #1"}]
    sm.workers[1] = w

    # With annotated=True, labels and bounding box are rendered
    ann = sm.get_latest_frame(1, annotated=True)
    assert not np.array_equal(ann, f)

    # With annotated=False, pristine raw frame is returned
    raw = sm.get_latest_frame(1, annotated=False)
    assert np.array_equal(raw, f)

    # With set_camera_labels(1, False), even annotated=True returns raw
    sm.set_camera_labels(1, False)
    assert np.array_equal(sm.get_latest_frame(1, annotated=True), f)



