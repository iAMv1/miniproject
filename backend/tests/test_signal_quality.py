from app.ml.signal_quality import assess_signal_quality


def test_low_activity_abstains_from_a_behavioral_conclusion():
    quality = assess_signal_quality(
        {
            "typing_speed_wpm": 0,
            "click_count": 0,
            "mouse_speed_mean": 0,
            "tab_switch_freq": 0,
            "session_duration_min": 0,
        },
        calibrated=True,
        model_ready=True,
    )
    assert quality["signal_state"] == "INSUFFICIENT_ACTIVITY"
    assert quality["input_quality"] == "low_activity"


def test_measured_uncalibrated_activity_is_labeled_as_calibrating():
    quality = assess_signal_quality(
        {
            "typing_speed_wpm": 42,
            "click_count": 10,
            "mouse_speed_mean": 320,
            "tab_switch_freq": 2,
            "session_duration_min": 5,
        },
        calibrated=False,
        model_ready=True,
    )
    assert quality["signal_state"] == "CALIBRATING"
    assert quality["input_quality"] == "population_prior"


def test_ready_requires_model_activity_and_personal_calibration():
    quality = assess_signal_quality(
        {
            "typing_speed_wpm": 42,
            "click_count": 10,
            "mouse_speed_mean": 320,
            "tab_switch_freq": 2,
            "session_duration_min": 5,
        },
        calibrated=True,
        model_ready=True,
    )
    assert quality["signal_state"] == "READY"
    assert quality["activity_features_observed"] == 5
