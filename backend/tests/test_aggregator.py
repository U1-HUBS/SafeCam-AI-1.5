import pytest
import time
from backend.services.ai_service import TemporalAggregator

def test_aggregator_no_trigger_on_single_frame():
    agg = TemporalAggregator(camera_id=1, window_seconds=6.0, positive_ratio=0.5, min_positive_frames=3, threshold=0.3)
    t = time.time()
    
    # Single positive frame
    res = agg.add_prediction(t, "a physical fight", "Suspected Fight", 0.75, True)
    assert res is None, "A single anomalous frame must not trigger an incident"


def test_aggregator_trigger_on_sustained_violence():
    agg = TemporalAggregator(camera_id=1, window_seconds=6.0, positive_ratio=0.5, min_positive_frames=3, threshold=0.3, cooldown_seconds=20.0)
    t = time.time()

    # Frame 1: positive
    agg.add_prediction(t, "a physical fight", "Suspected Fight", 0.65, True)
    # Frame 2: positive
    agg.add_prediction(t + 0.5, "a physical fight", "Suspected Fight", 0.70, True)
    # Frame 3: positive
    trigger = agg.add_prediction(t + 1.0, "a physical fight", "Suspected Fight", 0.75, True)

    assert trigger is not None, "Sustained positive frames must trigger an incident"
    assert trigger["camera_id"] == 1
    assert trigger["category"] == "Suspected Fight"
    assert trigger["severity"] in ["High", "Critical"]
    assert trigger["peak_confidence"] == pytest.approx(0.75)


def test_aggregator_cooldown_prevents_duplicate_spam():
    agg = TemporalAggregator(camera_id=1, window_seconds=6.0, positive_ratio=0.5, min_positive_frames=2, threshold=0.3, cooldown_seconds=15.0)
    t = time.time()

    # Trigger first incident
    agg.add_prediction(t, "a physical fight", "Suspected Fight", 0.7, True)
    trigger1 = agg.add_prediction(t + 0.5, "a physical fight", "Suspected Fight", 0.7, True)
    assert trigger1 is not None

    # Immediate next positive frame within cooldown (e.g. 2s later)
    trigger2 = agg.add_prediction(t + 2.0, "a physical fight", "Suspected Fight", 0.8, True)
    assert trigger2 is None, "Cooldown must prevent repeated alerts for the same ongoing incident"
