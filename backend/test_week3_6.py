"""
Unit tests for Week 3-6 ML improvements:
- Real Data Collection (Fix #3)
- Active Learning (Fix #7)
- Model Ensemble (Fix #4)
"""
import sys
import os
import json
import time
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.ml.real_data_collector import RealDataCollector
from app.ml.ensemble import StressEnsemble
from app.core.config import LABELS


class TestRealDataCollector(unittest.TestCase):
    """Test real data collection pipeline."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.collector = RealDataCollector(db_dir=self.tmpdir)
        self.sample_features = {
            "hold_time_mean": 120.0,
            "hold_time_std": 25.0,
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

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_self_report(self):
        """Self-report should save labeled sample."""
        row_id = self.collector.save_self_report(
            user_id="test_user",
            features=self.sample_features,
            label="STRESSED",
            model_prediction="MILD",
            model_confidence=0.6,
        )
        self.assertGreater(row_id, 0)

    def test_save_self_report_invalid_label(self):
        """Invalid label should raise ValueError."""
        with self.assertRaises(ValueError):
            self.collector.save_self_report(
                user_id="test_user",
                features=self.sample_features,
                label="INVALID",
            )

    def test_save_feedback_correction(self):
        """Feedback correction should save with correct source."""
        row_id = self.collector.save_feedback_correction(
            user_id="test_user",
            features=self.sample_features,
            model_prediction="STRESSED",
            actual_label="NEUTRAL",
            model_confidence=0.8,
        )
        self.assertGreater(row_id, 0)
        
        samples = self.collector.get_labeled_samples(
            user_id="test_user", source="feedback_correction"
        )
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["label"], "NEUTRAL")

    def test_save_intervention_outcome_accepted(self):
        """Accepted intervention should infer STRESSED/MILD label."""
        row_id = self.collector.save_intervention_outcome(
            user_id="test_user",
            intervention_type="breathing_reset",
            accepted=True,
            score_before=75.0,
        )
        self.assertGreater(row_id, 0)
        
        interventions = self.collector.get_intervention_labels(user_id="test_user")
        self.assertEqual(len(interventions), 1)
        self.assertEqual(interventions[0]["inferred_label"], "STRESSED")

    def test_save_intervention_outcome_rejected(self):
        """Rejected intervention should infer NEUTRAL label."""
        row_id = self.collector.save_intervention_outcome(
            user_id="test_user",
            intervention_type="breathing_reset",
            accepted=False,
            score_before=30.0,
        )
        self.assertGreater(row_id, 0)
        
        interventions = self.collector.get_intervention_labels(user_id="test_user")
        self.assertEqual(interventions[0]["inferred_label"], "NEUTRAL")

    def test_should_request_feedback_near_boundary_low_confidence(self):
        """Should ask when near boundary AND low confidence."""
        should_ask, reason = self.collector.should_request_feedback(
            score=70.0,  # Near MILD/STRESSED boundary
            confidence=0.4,  # Low confidence
            model_score=75.0,
            heuristic_score=50.0,
            user_id="test_user",
        )
        self.assertTrue(should_ask)
        self.assertIn("low_confidence", reason)

    def test_should_request_feedback_near_boundary_disagreement(self):
        """Should ask when near boundary AND model/heuristic disagree."""
        should_ask, reason = self.collector.should_request_feedback(
            score=40.0,  # Near NEUTRAL/MILD boundary
            confidence=0.7,  # Medium confidence
            model_score=80.0,
            heuristic_score=30.0,  # 50 point disagreement
            user_id="test_user",
        )
        self.assertTrue(should_ask)
        self.assertIn("model_disagreement", reason)

    def test_should_not_request_feedback_confident_agreement(self):
        """Should NOT ask when confident and models agree."""
        should_ask, reason = self.collector.should_request_feedback(
            score=20.0,  # Far from boundary
            confidence=0.9,  # High confidence
            model_score=25.0,
            heuristic_score=20.0,  # Small disagreement
            user_id="test_user",
        )
        self.assertFalse(should_ask)
        self.assertEqual(reason, "not_uncertain")

    def test_should_not_request_feedback_recently_asked(self):
        """Should NOT ask if recently asked (within interval)."""
        # First request
        self.collector.record_feedback_request(
            user_id="test_user",
            score=70.0,
            confidence=0.4,
            model_score=75.0,
            heuristic_score=50.0,
        )
        
        # Second request immediately after
        should_ask, reason = self.collector.should_request_feedback(
            score=70.0,
            confidence=0.4,
            model_score=75.0,
            heuristic_score=50.0,
            user_id="test_user",
            min_interval_minutes=30.0,
        )
        self.assertFalse(should_ask)
        self.assertEqual(reason, "recently_asked")

    def test_get_labeled_samples(self):
        """Should retrieve labeled samples with filters."""
        # Save 3 samples
        self.collector.save_self_report("user1", self.sample_features, "NEUTRAL")
        self.collector.save_self_report("user1", self.sample_features, "STRESSED")
        self.collector.save_self_report("user2", self.sample_features, "MILD")
        
        # Get all for user1
        samples = self.collector.get_labeled_samples(user_id="user1")
        self.assertEqual(len(samples), 2)
        
        # Get only STRESSED
        stressed = self.collector.get_labeled_samples(user_id="user1", label="STRESSED")
        self.assertEqual(len(stressed), 1)
        self.assertEqual(stressed[0]["label"], "STRESSED")

    def test_get_dataset_stats(self):
        """Should return correct statistics."""
        self.collector.save_self_report("user1", self.sample_features, "NEUTRAL")
        self.collector.save_self_report("user1", self.sample_features, "STRESSED")
        self.collector.save_feedback_correction(
            "user1", self.sample_features, "MILD", "NEUTRAL"
        )
        
        stats = self.collector.get_dataset_stats(user_id="user1")
        
        self.assertEqual(stats["total_labeled_samples"], 3)
        self.assertIn("NEUTRAL", stats["by_label"])
        self.assertIn("STRESSED", stats["by_label"])
        self.assertIn("self_report", stats["by_source"])
        self.assertIn("feedback_correction", stats["by_source"])

    def test_export_for_training(self):
        """Should export data in training format when enough samples."""
        # Need at least 50 samples
        for i in range(55):
            label = ["NEUTRAL", "MILD", "STRESSED"][i % 3]
            self.collector.save_self_report("user1", self.sample_features, label)
        
        result = self.collector.export_for_training(user_id="user1", min_samples=50)
        
        self.assertIsNotNone(result)
        features, labels = result
        self.assertEqual(len(features), 55)
        self.assertEqual(len(labels), 55)

    def test_export_for_training_insufficient_data(self):
        """Should return None when not enough samples."""
        self.collector.save_self_report("user1", self.sample_features, "NEUTRAL")
        
        result = self.collector.export_for_training(user_id="user1", min_samples=50)
        self.assertIsNone(result)


class TestStressEnsemble(unittest.TestCase):
    """Test ensemble model."""

    def test_ensemble_initialization(self):
        """Ensemble should initialize without errors."""
        ens = StressEnsemble()
        self.assertIsNotNone(ens)
        self.assertFalse(ens.is_ready)  # Not loaded yet

    def test_fallback_result(self):
        """Fallback should return valid structure."""
        ens = StressEnsemble()
        result = ens._fallback_result()
        
        self.assertIn("probabilities", result)
        self.assertIn("prediction", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["n_models_used"], 0)

    def test_update_weights(self):
        """Weight update should normalize correctly."""
        ens = StressEnsemble()
        ens.update_weights(0.6, 0.2, 0.2)
        
        self.assertAlmostEqual(ens._model_weights["xgb"], 0.6)
        self.assertAlmostEqual(ens._model_weights["rf"], 0.2)
        self.assertAlmostEqual(ens._model_weights["lgb"], 0.2)

    def test_update_weights_normalization(self):
        """Weights should normalize to sum to 1."""
        ens = StressEnsemble()
        ens.update_weights(3.0, 1.0, 1.0)  # Unnormalized
        
        total = sum(ens._model_weights.values())
        self.assertAlmostEqual(total, 1.0)


class TestIntegration(unittest.TestCase):
    """Integration tests for data collection + active learning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.collector = RealDataCollector(db_dir=self.tmpdir)
        self.sample_features = {
            "hold_time_mean": 120.0,
            "typing_speed_wpm": 45.0,
            "error_rate": 0.12,
        }

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_feedback_loop(self):
        """Test complete feedback collection and retrieval."""
        user_id = "test_user"
        
        # 1. Model makes prediction
        model_pred = "STRESSED"
        model_conf = 0.55
        
        # 2. System decides to ask for feedback
        should_ask, reason = self.collector.should_request_feedback(
            score=68.0,
            confidence=model_conf,
            model_score=70.0,
            heuristic_score=35.0,
            user_id=user_id,
        )
        self.assertTrue(should_ask)
        
        # 3. Record that request was shown
        req_id = self.collector.record_feedback_request(
            user_id=user_id,
            score=68.0,
            confidence=model_conf,
            model_score=70.0,
            heuristic_score=35.0,
        )
        
        # 4. User provides correction
        self.collector.save_feedback_correction(
            user_id=user_id,
            features=self.sample_features,
            model_prediction=model_pred,
            actual_label="MILD",
            model_confidence=model_conf,
        )
        
        # 5. Verify data stored correctly
        samples = self.collector.get_labeled_samples(
            user_id=user_id, source="feedback_correction"
        )
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["label"], "MILD")
        self.assertEqual(samples[0]["model_prediction"], "STRESSED")

    def test_intervention_correlation_loop(self):
        """Test intervention-based labeling."""
        user_id = "test_user"
        
        # 1. System recommends break (score = 75, STRESSED)
        score_before = 75.0
        
        # 2. User accepts break
        self.collector.save_intervention_outcome(
            user_id=user_id,
            intervention_type="breathing_reset",
            accepted=True,
            score_before=score_before,
            score_after=45.0,
        )
        
        # 3. Verify inferred label
        interventions = self.collector.get_intervention_labels(user_id=user_id)
        self.assertEqual(interventions[0]["inferred_label"], "STRESSED")
        
        # 4. Score dropped after intervention (break worked)
        self.assertLess(interventions[0]["score_after"], interventions[0]["score_before"])


if __name__ == "__main__":
    unittest.main()
