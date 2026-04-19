"""
Unit tests for dynamic hybrid weighting (Issue #2 fix)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

import unittest
from app.services.inference import compute_adaptive_weight, InferenceEngine
from app.core.config import MODEL_SCORE_WEIGHT


class TestDynamicWeighting(unittest.TestCase):
    """Test the adaptive weight computation for ML/heuristic blend."""

    def test_high_confidence_gets_high_weight(self):
        """High confidence (>0.8) should increase ML weight."""
        weight = compute_adaptive_weight(
            confidence=0.9,
            is_calibrated=True,
            model_score=75.0,
            equation_score=60.0,
        )
        # Base 0.7 + 0.15 for high confidence = 0.85
        self.assertGreater(weight, 0.8)
        self.assertLessEqual(weight, 0.9)

    def test_low_confidence_gets_low_weight(self):
        """Low confidence (<0.5) should decrease ML weight."""
        weight = compute_adaptive_weight(
            confidence=0.4,
            is_calibrated=True,
            model_score=75.0,
            equation_score=60.0,
        )
        # Base 0.7 - 0.15 for low confidence = 0.55
        self.assertLess(weight, 0.6)
        self.assertGreaterEqual(weight, 0.5)

    def test_uncalibrated_gets_conservative_weight(self):
        """Uncalibrated users should get more conservative weighting."""
        weight_calibrated = compute_adaptive_weight(
            confidence=0.9,
            is_calibrated=True,
            model_score=75.0,
            equation_score=60.0,
        )
        weight_uncalibrated = compute_adaptive_weight(
            confidence=0.9,
            is_calibrated=False,
            model_score=75.0,
            equation_score=60.0,
        )
        # Uncalibrated should be lower (more conservative)
        self.assertLess(weight_uncalibrated, weight_calibrated)
        self.assertLess(weight_uncalibrated, 0.8)

    def test_disagreement_reduces_weight(self):
        """Large ML/heuristic disagreement should reduce ML weight."""
        weight_agree = compute_adaptive_weight(
            confidence=0.8,
            is_calibrated=True,
            model_score=65.0,
            equation_score=60.0,  # Small disagreement (5 points)
        )
        weight_disagree = compute_adaptive_weight(
            confidence=0.8,
            is_calibrated=True,
            model_score=80.0,
            equation_score=40.0,  # Large disagreement (40 points)
        )
        # Disagreement should result in lower weight
        self.assertLess(weight_disagree, weight_agree)

    def test_weight_bounds(self):
        """Weight should always be in [0.5, 0.9] range."""
        test_cases = [
            (0.95, True, 50.0, 50.0),   # Very high confidence
            (0.1, False, 90.0, 10.0),   # Very low confidence, uncalibrated, big disagreement
            (0.6, True, 50.0, 50.0),    # Medium confidence
            (0.8, False, 70.0, 30.0),  # High confidence but uncalibrated with disagreement
        ]
        for conf, cal, m_score, e_score in test_cases:
            weight = compute_adaptive_weight(conf, cal, m_score, e_score)
            self.assertGreaterEqual(weight, 0.5, f"Weight {weight} below minimum")
            self.assertLessEqual(weight, 0.9, f"Weight {weight} above maximum")

    def test_neutral_case(self):
        """Medium confidence, calibrated, no disagreement = base weight."""
        weight = compute_adaptive_weight(
            confidence=0.6,
            is_calibrated=True,
            model_score=70.0,
            equation_score=70.0,
        )
        # Should be close to base weight (0.7)
        self.assertAlmostEqual(weight, MODEL_SCORE_WEIGHT, delta=0.01)


class TestInferenceEngine(unittest.TestCase):
    """Test the inference engine with dynamic weighting."""

    def setUp(self):
        self.engine = InferenceEngine()

    def test_engine_initialization(self):
        """Engine should initialize without errors."""
        self.assertIsNotNone(self.engine)
        self.assertFalse(self.engine.is_ready)  # Not loaded yet

    def test_fallback_result(self):
        """Fallback result should have required fields."""
        result = self.engine._fallback_result("Test message")
        
        required_fields = [
            "score", "model_score", "equation_score", "final_score",
            "level", "confidence", "probabilities", "insights", "timestamp"
        ]
        for field in required_fields:
            self.assertIn(field, result)

    def test_level_from_score(self):
        """Score to level mapping should be correct."""
        self.assertEqual(self.engine._level_from_score(20.0), "NEUTRAL")
        self.assertEqual(self.engine._level_from_score(50.0), "MILD")
        self.assertEqual(self.engine._level_from_score(80.0), "STRESSED")


class TestFeatureInteractions(unittest.TestCase):
    """Test feature interaction computation (Issue #3)."""

    def test_interaction_features_exist(self):
        """Interaction feature names should be defined."""
        from app.core.config import INTERACTION_FEATURE_NAMES
        
        self.assertEqual(len(INTERACTION_FEATURE_NAMES), 5)
        expected = [
            "typing_speed_wpm_x_error_rate",
            "rage_click_count_x_direction_change_rate",
            "session_fragmentation_x_tab_switch_freq",
            "pause_frequency_x_rhythm_entropy",
            "mouse_speed_std_x_click_count",
        ]
        for name in expected:
            self.assertIn(name, INTERACTION_FEATURE_NAMES)

    def test_compute_interactions(self):
        """Interaction features should be computable."""
        from app.ml.feature_extractor import compute_interaction_features
        
        # Sample features
        features = {
            "typing_speed_wpm": 45.0,
            "error_rate": 0.12,
            "rage_click_count": 3.0,
            "direction_change_rate": 0.7,
            "session_fragmentation": 0.8,
            "tab_switch_freq": 12.0,
            "pause_frequency": 2.5,
            "rhythm_entropy": 3.5,
            "mouse_speed_std": 150.0,
            "click_count": 25.0,
        }
        
        interactions = compute_interaction_features(features)
        
        # Should have 5 interactions
        self.assertEqual(len(interactions), 5)
        
        # All values should be positive (log1p + 0.01)
        for name, value in interactions.items():
            self.assertGreater(value, 0.0)
            self.assertIn("_x_", name)  # Naming convention


if __name__ == "__main__":
    unittest.main()
