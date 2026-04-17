"""MindPulse Backend — Inference Service."""

from __future__ import annotations
import logging
import numpy as np
import time
from typing import Dict, List, Optional

from app.core.config import (
    FEATURE_NAMES,
    LABELS,
    STRESS_SCORE_THRESHOLD_MILD,
    STRESS_SCORE_THRESHOLD_HIGH,
    MODEL_SCORE_WEIGHT,
)

logger = logging.getLogger("mindpulse.inference")


class InferenceEngine:
    """Wraps XGBoost model + DualNormalizer for stress prediction with SHAP explainability."""

    def __init__(self):
        self._model = None
        self._stats = None
        self._normalizer = None
        self._baselines = {}
        self._ready = False
        self._shap_explainer = None

    @staticmethod
    def _sigmoid(x: float) -> float:
        x = max(min(x, 8.0), -8.0)
        return 1.0 / (1.0 + np.exp(-x))

    @staticmethod
    def _clamp_score(x: float) -> float:
        return float(max(0.0, min(100.0, x)))

    def _feature_risk(
        self, z_values: dict, name: str, invert: bool = False, default: float = 0.0
    ) -> float:
        z = float(z_values.get(name, default))
        z = -z if invert else z
        return float(self._sigmoid(z))

    def _compute_equation_score(
        self, features: dict, raw: np.ndarray, baseline, hour: int
    ) -> tuple[float, dict]:
        z_values = {}

        try:
            if baseline is not None and baseline.is_calibrated():
                z_user = baseline.compute_deviations(raw, hour)
                z_values = {
                    name: float(z_user[i]) for i, name in enumerate(FEATURE_NAMES)
                }
            elif self._stats is not None:
                mean = np.asarray(self._stats["mean"], dtype=np.float32)
                std = np.asarray(self._stats["std"], dtype=np.float32) + 1e-8
                z_global = (raw - mean) / std
                z_values = {
                    name: float(z_global[i]) for i, name in enumerate(FEATURE_NAMES)
                }
        except Exception:
            z_values = {}

        keyboard = np.mean(
            [
                self._feature_risk(z_values, "hold_time_std"),
                self._feature_risk(z_values, "flight_time_std"),
                self._feature_risk(z_values, "pause_frequency"),
                self._feature_risk(z_values, "rhythm_entropy"),
                self._feature_risk(z_values, "error_rate"),
            ]
        )
        speed = self._feature_risk(z_values, "typing_speed_wpm", invert=True)
        switching = np.mean(
            [
                self._feature_risk(z_values, "tab_switch_freq"),
                self._feature_risk(z_values, "switch_entropy"),
                self._feature_risk(z_values, "session_fragmentation"),
            ]
        )
        mouse = np.mean(
            [
                self._feature_risk(z_values, "mouse_speed_std"),
                self._feature_risk(z_values, "direction_change_rate"),
                self._feature_risk(z_values, "rage_click_count"),
            ]
        )

        reentry_count = float(features.get("mouse_reentry_count", 0.0))
        reentry_latency = float(features.get("mouse_reentry_latency_ms", 0.0))
        reentry = np.mean(
            [
                self._sigmoid((reentry_count - 1.0) / 2.0),
                self._sigmoid((reentry_latency - 3000.0) / 1500.0),
            ]
        )

        contributions = {
            "S_keyboard": round(float(keyboard) * 100.0, 1),
            "S_speed": round(float(speed) * 100.0, 1),
            "S_switching": round(float(switching) * 100.0, 1),
            "S_mouse": round(float(mouse) * 100.0, 1),
            "S_reentry": round(float(reentry) * 100.0, 1),
        }

        equation_score = (
            0.30 * contributions["S_keyboard"]
            + 0.15 * contributions["S_speed"]
            + 0.25 * contributions["S_switching"]
            + 0.20 * contributions["S_mouse"]
            + 0.10 * contributions["S_reentry"]
        )
        return self._clamp_score(float(equation_score)), contributions

    @staticmethod
    def _level_from_score(score: float) -> str:
        if score >= STRESS_SCORE_THRESHOLD_HIGH:
            return "STRESSED"
        if score >= STRESS_SCORE_THRESHOLD_MILD:
            return "MILD"
        return "NEUTRAL"

    def load(self):
        """Lazy-load model from ml package."""
        if self._ready:
            return
        try:
            from app.ml.model import load_model, DualNormalizer

            self._model, self._stats = load_model(
                allow_download=True, allow_train_fallback=True
            )
            self._normalizer = DualNormalizer(self._stats)
            self._ready = True
            logger.info("Model loaded successfully")

            try:
                import shap

                self._shap_explainer = shap.TreeExplainer(self._model)
                logger.info("SHAP explainer initialized")
            except Exception as e:
                logger.warning(f"SHAP explainer unavailable: {e}")
                self._shap_explainer = None
        except Exception as e:
            logger.error(f"Model load failed: {e}")
            self._ready = False

    def _get_baseline(self, user_id: str):
        """Get or create a PersonalBaseline for a user."""
        if user_id not in self._baselines:
            try:
                from app.ml.model import PersonalBaseline, BASELINE_DB
                import os

                db_path = BASELINE_DB.replace(".db", f"_{user_id}.db")
                self._baselines[user_id] = PersonalBaseline(db_path=db_path)
            except Exception:
                self._baselines[user_id] = None
        return self._baselines[user_id]

    @property
    def is_ready(self) -> bool:
        return self._ready and self._model is not None

    def _compute_shap_values(self, z: np.ndarray) -> Optional[dict]:
        """Compute SHAP values for feature-level explainability."""
        if self._shap_explainer is None:
            return None
        try:
            shap_values = self._shap_explainer.shap_values(z.reshape(1, -1))
            # Handle multi-class output (list of arrays) or single array
            if isinstance(shap_values, list):
                # For multi-class, use STRESSED class (index 2)
                shap_values = (
                    shap_values[2] if len(shap_values) > 2 else shap_values[-1]
                )

            # Ensure shap_values is a 2D array
            if shap_values.ndim == 1:
                shap_values = shap_values.reshape(1, -1)

            shap_dict = {}
            num_features = len(FEATURE_NAMES)

            for i, name in enumerate(FEATURE_NAMES):
                # For dual normalization, we have 2x features (global + user)
                # Take whichever index exists
                idx = i if i < shap_values.shape[1] else i % num_features
                if idx < shap_values.shape[1]:
                    val = float(shap_values[0, idx])
                    if abs(val) > 0.001:
                        shap_dict[name] = round(val, 4)

            return (
                dict(sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True))
                if shap_dict
                else None
            )
        except Exception as e:
            logger.warning(f"SHAP computation failed: {e}")
            return None

    def predict(self, features_dict: dict, user_id: str = "default") -> dict:
        """Run inference and return structured result."""
        missing = [f for f in FEATURE_NAMES if f not in features_dict]
        if missing:
            preview = ", ".join(missing[:3])
            if len(missing) > 3:
                preview = f"{preview}, ... (+{len(missing) - 3} more)"
            return self._fallback_result(
                message=f"Missing required features: {preview}"
            )

        raw = np.array([features_dict[f] for f in FEATURE_NAMES], dtype=np.float32)

        hour = int(features_dict.get("hour_of_day", 12))
        baseline = self._get_baseline(user_id)
        equation_score, contributions = self._compute_equation_score(
            features_dict, raw, baseline, hour
        )

        shap_values = None

        if not self.is_ready:
            model_score = 0.0
            final_score = equation_score
            level = self._level_from_score(final_score)
            confidence = 0.45
            probs = np.array([0.33, 0.33, 0.34], dtype=np.float32)
        else:
            z = self._normalizer.transform(raw, hour, baseline)

            probs = self._model.predict_proba(z.reshape(1, -1))[0]
            confidence = float(np.max(probs))
            model_score = float(probs[0] * 5.0 + probs[1] * 55.0 + probs[2] * 100.0)
            final_score = (
                MODEL_SCORE_WEIGHT * model_score
                + (1.0 - MODEL_SCORE_WEIGHT) * equation_score
            )
            final_score = self._clamp_score(final_score)
            level = self._level_from_score(final_score)

            shap_values = self._compute_shap_values(z)

        timestamp = time.time()

        if baseline:
            baseline.update(raw, hour)
            baseline.save_session_score(timestamp * 1000.0, final_score, level)

        insights = self._generate_insights(features_dict, level, shap_values)

        return {
            "score": round(final_score, 1),
            "model_score": round(model_score, 1),
            "equation_score": round(equation_score, 1),
            "final_score": round(final_score, 1),
            "level": level,
            "confidence": round(confidence, 3),
            "probabilities": {l: round(float(p), 3) for l, p in zip(LABELS, probs)},
            "feature_contributions": contributions,
            "shap_values": shap_values,
            "insights": insights,
            "timestamp": timestamp,
            "typing_speed_wpm": round(
                float(features_dict.get("typing_speed_wpm", 0)), 1
            ),
            "rage_click_count": int(features_dict.get("rage_click_count", 0)),
            "error_rate": round(float(features_dict.get("error_rate", 0)), 3),
            "click_count": int(features_dict.get("click_count", 0)),
            "mouse_speed_mean": round(
                float(features_dict.get("mouse_speed_mean", 0)), 1
            ),
            "mouse_reentry_count": round(
                float(features_dict.get("mouse_reentry_count", 0)), 1
            ),
            "mouse_reentry_latency_ms": round(
                float(features_dict.get("mouse_reentry_latency_ms", 0)), 1
            ),
        }

    def _generate_insights(
        self, features: dict, level: str, shap_values: Optional[dict] = None
    ) -> List[str]:
        """Generate human-readable stress insights from feature values and SHAP."""
        insights = []

        if shap_values:
            top_features = list(shap_values.items())[:3]
            for feat_name, impact in top_features:
                direction = "increasing" if impact > 0 else "decreasing"
                readable = feat_name.replace("_", " ")
                if impact > 0:
                    insights.append(
                        f"{readable.capitalize()} is {direction} stress likelihood"
                    )
                else:
                    insights.append(
                        f"{readable.capitalize()} is {direction} stress likelihood"
                    )

        if features.get("rage_click_count", 0) > 2:
            insights.append(
                "Frustrated clicking detected — consider taking a short break"
            )
        if features.get("error_rate", 0) > 0.1:
            insights.append("Higher than usual error rate — possible cognitive fatigue")
        if features.get("rhythm_entropy", 0) > 3.5:
            insights.append("Typing rhythm is erratic — stress may be affecting focus")
        if features.get("session_fragmentation", 0) > 0.7:
            insights.append(
                "Highly fragmented session — frequent context switching detected"
            )
        if features.get("tab_switch_freq", 0) > 10:
            insights.append("Rapid app switching — may indicate difficulty focusing")
        if features.get("typing_speed_wpm", 50) < 30:
            insights.append("Typing speed is lower than typical — possible fatigue")
        if features.get("mouse_speed_std", 0) > 150:
            insights.append("Inconsistent mouse movements — possible restlessness")
        if features.get("mouse_reentry_count", 0) > 2:
            insights.append(
                "Frequent mouse re-entry after switches — possible task thrashing"
            )

        if not insights and level == "STRESSED":
            insights.append("Multiple behavioral signals indicate elevated stress")

        seen = set()
        unique_insights = []
        for i in insights:
            if i not in seen:
                seen.add(i)
                unique_insights.append(i)

        return unique_insights[:3]

    def _fallback_result(
        self, message: str = "Model not loaded — check server logs"
    ) -> dict:
        """Return when model is not loaded."""
        return {
            "score": 0.0,
            "model_score": 0.0,
            "equation_score": 0.0,
            "final_score": 0.0,
            "level": "UNKNOWN",
            "confidence": 0.0,
            "probabilities": {"NEUTRAL": 0.33, "MILD": 0.33, "STRESSED": 0.34},
            "feature_contributions": {},
            "shap_values": None,
            "insights": [message],
            "timestamp": time.time(),
            "typing_speed_wpm": 0.0,
            "rage_click_count": 0,
            "error_rate": 0.0,
            "click_count": 0,
            "mouse_speed_mean": 0.0,
            "mouse_reentry_count": 0.0,
            "mouse_reentry_latency_ms": 0.0,
        }


engine = InferenceEngine()
