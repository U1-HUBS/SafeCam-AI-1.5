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
