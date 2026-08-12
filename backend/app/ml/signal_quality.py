"""Input-quality contract for MindPulse behavioral signal inference.

The model observes interaction behavior, not stress directly. This module keeps
that limitation explicit at runtime by separating a numeric score from whether
there is enough measured activity and personal calibration to present it as a
useful behavioral signal.
"""
from __future__ import annotations

from typing import Mapping

ACTIVITY_FEATURES = (
    "typing_speed_wpm",
    "click_count",
    "mouse_speed_mean",
    "tab_switch_freq",
    "session_duration_min",
)


def assess_signal_quality(
    features: Mapping[str, float], *, calibrated: bool, model_ready: bool
) -> dict[str, object]:
    """Return a conservative product-facing signal state.

    `INSUFFICIENT_ACTIVITY` is intentionally distinct from a low score: a
    quiet window does not mean a user is relaxed. `CALIBRATING` is usable for
    trend collection but must not be presented as a personalized conclusion.
    """
    observed_activity = sum(
        1
        for name in ACTIVITY_FEATURES
        if abs(float(features.get(name, 0.0))) > 1e-9
    )
    if not model_ready:
        return {
            "signal_state": "UNAVAILABLE",
            "input_quality": "model_unavailable",
            "activity_features_observed": observed_activity,
            "message": "The behavioral signal is temporarily unavailable.",
        }
    if observed_activity < 2:
        return {
            "signal_state": "INSUFFICIENT_ACTIVITY",
            "input_quality": "low_activity",
            "activity_features_observed": observed_activity,
            "message": "Not enough interaction activity in this window to draw a useful signal.",
        }
    if not calibrated:
        return {
            "signal_state": "CALIBRATING",
            "input_quality": "population_prior",
            "activity_features_observed": observed_activity,
            "message": "MindPulse is learning your normal rhythm; treat this as an early trend, not a personal conclusion.",
        }
    return {
        "signal_state": "READY",
        "input_quality": "measured_activity",
        "activity_features_observed": observed_activity,
        "message": "Signal is based on measured interaction activity and your personal baseline.",
    }
