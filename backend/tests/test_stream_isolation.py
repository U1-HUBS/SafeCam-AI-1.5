import time
import pytest
import numpy as np
import cv2

from backend.services.ai_service import ViolenceClassifier, KineticMotionEstimator

def test_multi_camera_motion_isolation():
    """
    Verifies that alternating frames from 4 completely different camera scenes
    do NOT cross-pollinate motion diffs or trigger false violence.
    """
    classifier = ViolenceClassifier(use_gpu=False)
    t = time.time()

    # Generate 4 distinct calm camera scenes with different brightness and text
    cam_frames = {}
    for cam_id in [1, 2, 3, 4]:
        frame = np.full((240, 320, 3), 40 * cam_id, dtype=np.uint8)
        cv2.putText(frame, f"CAM {cam_id} VIEW", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cam_frames[cam_id] = frame

    # Simulate Round 1 (initial frame for each camera)
    for cam_id in [1, 2, 3, 4]:
        label, cat, conf, is_violent = classifier.predict_frame(
            cam_frames[cam_id],
            timestamp=t,
            camera_id=cam_id
        )
        assert not is_violent
        assert conf < 0.30

    # Simulate Round 2 (subsequent frames interleaved across cameras)
    for i in range(5):
        t += 0.5
        for cam_id in [1, 2, 3, 4]:
            label, cat, conf, is_violent = classifier.predict_frame(
                cam_frames[cam_id],
                timestamp=t,
                camera_id=cam_id
            )
            assert not is_violent, f"Camera {cam_id} falsely triggered violence due to cross-camera pollution on step {i}"
            assert conf < 0.25

def test_single_camera_violence_isolation():
    """
    Verifies that when Camera 1 experiences a violent altercation,
    ONLY Camera 1 triggers violence alerts while Cameras 2, 3, and 4 stay peaceful.
    """
    classifier = ViolenceClassifier(use_gpu=False)
    t = time.time()

    # Setup 4 cameras
    # Camera 1: altercation simulation
    cam1_f1 = np.full((240, 320, 3), 90, dtype=np.uint8)
    cv2.circle(cam1_f1, (140, 120), 25, (30, 30, 200), -1)
    cv2.circle(cam1_f1, (180, 120), 25, (200, 30, 30), -1)

    cam1_f2 = np.full((240, 320, 3), 90, dtype=np.uint8)
    cv2.circle(cam1_f2, (160, 145), 30, (30, 30, 220), -1)
    cv2.circle(cam1_f2, (150, 95), 30, (220, 30, 30), -1)
    cv2.line(cam1_f2, (130, 110), (180, 130), (255, 255, 255), 5)

    # Cameras 2, 3, 4: peaceful hallway scenes
    peaceful_frames = {}
    for cid in [2, 3, 4]:
        frame = np.full((240, 320, 3), 120, dtype=np.uint8)
        cv2.putText(frame, f"Hallway {cid}", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (20, 20, 20), 1)
        peaceful_frames[cid] = frame

    # Baseline frame for all
    classifier.predict_frame(cam1_f1, timestamp=t, camera_id=1)
    for cid in [2, 3, 4]:
        classifier.predict_frame(peaceful_frames[cid], timestamp=t, camera_id=cid)

    # Next step: Cam 1 has violent struggle, Cams 2, 3, 4 stay calm
    t += 0.5
    res1 = classifier.predict_frame(cam1_f2, timestamp=t, camera_id=1)
    res2 = classifier.predict_frame(peaceful_frames[2], timestamp=t, camera_id=2)
    res3 = classifier.predict_frame(peaceful_frames[3], timestamp=t, camera_id=3)
    res4 = classifier.predict_frame(peaceful_frames[4], timestamp=t, camera_id=4)

    # Camera 1 MUST detect violence
    assert res1[3] is True, "Camera 1 should detect violence from the altercation"
    assert res1[2] >= 0.50

    # Cameras 2, 3, 4 MUST NOT detect violence
    assert res2[3] is False, "Camera 2 must remain peaceful"
    assert res3[3] is False, "Camera 3 must remain peaceful"
    assert res4[3] is False, "Camera 4 must remain peaceful"

    assert res2[2] < 0.25
    assert res3[2] < 0.25
    assert res4[2] < 0.25

def test_dedicated_worker_motion_estimator():
    """
    Tests passing a dedicated per-worker KineticMotionEstimator directly to predict_frame.
    """
    classifier = ViolenceClassifier(use_gpu=False)
    estimator_cam1 = KineticMotionEstimator()
    estimator_cam2 = KineticMotionEstimator()

    frame_a = np.full((240, 320, 3), 50, dtype=np.uint8)
    frame_b = np.full((240, 320, 3), 200, dtype=np.uint8)

    t = time.time()
    # Cam 1 baseline
    classifier.predict_frame(frame_a, t, motion_estimator=estimator_cam1)
    # Cam 2 baseline
    classifier.predict_frame(frame_b, t, motion_estimator=estimator_cam2)

    # Next step: identical frames for each camera
    t += 0.5
    res_a = classifier.predict_frame(frame_a, t, motion_estimator=estimator_cam1)
    res_b = classifier.predict_frame(frame_b, t, motion_estimator=estimator_cam2)

    # Neither should trigger motion or violence
    assert not res_a[3]
    assert not res_b[3]
