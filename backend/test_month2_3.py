"""
Unit tests for Month 2-3 ML improvements:
- Temporal LSTM Model (Fix #5)
- Online Learning Pipeline (Fix #6)
"""
import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app.ml.temporal_model import StressLSTM, SEQUENCE_LENGTH, FEATURE_DIM
from app.ml.online_learning import OnlineLearner
from app.core.config import LABELS, FEATURE_NAMES


class TestTemporalLSTM(unittest.TestCase):
    """Test LSTM temporal model."""

    def setUp(self):
        self.lstm = StressLSTM(hidden_size=32, num_layers=1, dropout=0.1)
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_lstm_initialization(self):
        """LSTM should initialize without errors."""
        self.assertIsNotNone(self.lstm)
        self.assertFalse(self.lstm.is_ready)

    def test_fallback_result(self):
        """Fallback should return valid structure."""
        result = self.lstm._fallback_result()
        
        self.assertIn("probabilities", result)
        self.assertIn("prediction", result)
        self.assertIn("confidence", result)
        self.assertEqual(result["model_type"], "lstm_temporal")

    def test_predict_sequence_not_ready(self):
        """Should return fallback when not trained."""
        sequence = [[0.0] * FEATURE_DIM] * SEQUENCE_LENGTH
        import numpy as np
        result = self.lstm.predict_sequence(np.array(sequence, dtype=np.float32))
        
        self.assertEqual(result["prediction"], "NEUTRAL")
        self.assertEqual(result["confidence"], 0.34)

    def test_generate_synthetic_sequences(self):
        """Should generate valid training sequences."""
        sequences, labels = self.lstm.generate_synthetic_sequences(n_samples=100)
        
        self.assertEqual(sequences.shape[0], 100)
        self.assertEqual(sequences.shape[1], SEQUENCE_LENGTH)
        self.assertEqual(sequences.shape[2], FEATURE_DIM)
        self.assertEqual(labels.shape[0], 100)
        
        # Check label distribution
        unique, counts = np.unique(labels, return_counts=True)
        self.assertGreater(len(unique), 1)  # Should have multiple classes

    def test_sequence_dimensions(self):
        """Generated sequences should have correct dimensions."""
        import numpy as np
        sequences, labels = self.lstm.generate_synthetic_sequences(n_samples=50)
        
        self.assertEqual(sequences.ndim, 3)  # [batch, seq_len, features]
        self.assertEqual(sequences.shape[1], SEQUENCE_LENGTH)
        self.assertEqual(sequences.shape[2], FEATURE_DIM)


class TestOnlineLearning(unittest.TestCase):
    """Test online learning pipeline."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.learner = OnlineLearner(db_dir=self.tmpdir)
        self.sample_features = {
            "hold_time_mean": 120.0,
            "typing_speed_wpm": 45.0,
            "error_rate": 0.12,
        }

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_adapter_new_user(self):
        """New user should get default adapter."""
        adapter = self.learner.get_adapter("new_user")
        
        self.assertEqual(adapter["threshold_adjustment"], 0.0)
        self.assertEqual(adapter["weight_multiplier"], 1.0)
        self.assertEqual(adapter["class_bias"]["NEUTRAL"], 0.0)
        self.assertEqual(adapter["class_bias"]["MILD"], 0.0)
        self.assertEqual(adapter["class_bias"]["STRESSED"], 0.0)

    def test_update_from_feedback_false_positive(self):
        """False positive should decrease threshold."""
        adapter = self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="STRESSED",
            actual="NEUTRAL",
            score=75.0,
        )
        
        self.assertLess(adapter["threshold_adjustment"], 0.0)
        self.assertLess(adapter["class_bias"]["STRESSED"], 0.0)
        self.assertEqual(adapter["n_updates"], 1)

    def test_update_from_feedback_false_negative(self):
        """False negative should increase threshold."""
        adapter = self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="NEUTRAL",
            actual="STRESSED",
            score=20.0,
        )
        
        self.assertGreater(adapter["threshold_adjustment"], 0.0)
        self.assertGreater(adapter["class_bias"]["STRESSED"], 0.0)

    def test_update_from_feedback_wrong_class(self):
        """Wrong class should adjust specific class biases."""
        adapter = self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="MILD",
            actual="STRESSED",
            score=50.0,
        )
        
        self.assertLess(adapter["class_bias"]["MILD"], 0.0)
        self.assertGreater(adapter["class_bias"]["STRESSED"], 0.0)

    def test_adapter_clamping(self):
        """Adapter values should be clamped to prevent extremes."""
        # Apply many updates
        for _ in range(100):
            self.learner.update_from_feedback(
                user_id="test_user",
                features=self.sample_features,
                predicted="STRESSED",
                actual="NEUTRAL",
                score=80.0,
            )
        
        adapter = self.learner.get_adapter("test_user")
        
        self.assertGreaterEqual(adapter["threshold_adjustment"], -15.0)
        self.assertLessEqual(adapter["threshold_adjustment"], 15.0)
        for cls in adapter["class_bias"]:
            self.assertGreaterEqual(adapter["class_bias"][cls], -0.3)
            self.assertLessEqual(adapter["class_bias"][cls], 0.3)

    def test_apply_adapter(self):
        """Adapter should adjust score and probabilities."""
        # First create some adjustments
        self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="NEUTRAL",
            actual="STRESSED",
            score=20.0,
        )
        
        score, probs = self.learner.apply_adapter(
            user_id="test_user",
            score=50.0,
            probabilities={"NEUTRAL": 0.33, "MILD": 0.33, "STRESSED": 0.34},
        )
        
        # Score should be adjusted upward (user tends to be more stressed)
        self.assertGreater(score, 50.0)
        
        # Probabilities should still sum to ~1.0
        total = sum(probs.values())
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_apply_adapter_no_adjustment(self):
        """New user adapter should not change predictions."""
        score, probs = self.learner.apply_adapter(
            user_id="new_user",
            score=50.0,
            probabilities={"NEUTRAL": 0.33, "MILD": 0.33, "STRESSED": 0.34},
        )
        
        self.assertAlmostEqual(score, 50.0, places=1)

    def test_experience_buffer(self):
        """Experience buffer should store and retrieve samples."""
        self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="STRESSED",
            actual="NEUTRAL",
            score=75.0,
        )
        
        samples = self.learner.get_experience_buffer(user_id="test_user")
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["predicted"], "STRESSED")
        self.assertEqual(samples[0]["actual"], "NEUTRAL")

    def test_mark_experience_used(self):
        """Should mark samples as used for training."""
        self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="STRESSED",
            actual="NEUTRAL",
            score=75.0,
        )
        
        samples = self.learner.get_experience_buffer(user_id="test_user")
        self.learner.mark_experience_used([samples[0]["id"]])
        
        # Should not appear in unused list
        unused = self.learner.get_experience_buffer(user_id="test_user", used_only=False)
        self.assertEqual(len(unused), 0)

    def test_prepare_retraining_data(self):
        """Should prepare data when enough samples exist."""
        for i in range(110):
            self.learner.update_from_feedback(
                user_id="test_user",
                features=self.sample_features,
                predicted=["NEUTRAL", "MILD", "STRESSED"][i % 3],
                actual=["NEUTRAL", "MILD", "STRESSED"][(i + 1) % 3],
                score=50.0,
            )
        
        result = self.learner.prepare_retraining_data(
            user_id="test_user", min_samples=100
        )
        
        self.assertIsNotNone(result)
        features, labels = result
        self.assertEqual(len(features), 110)
        self.assertEqual(len(labels), 110)

    def test_prepare_retraining_data_insufficient(self):
        """Should return None when not enough samples."""
        self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="STRESSED",
            actual="NEUTRAL",
            score=75.0,
        )
        
        result = self.learner.prepare_retraining_data(
            user_id="test_user", min_samples=100
        )
        self.assertIsNone(result)

    def test_get_user_stats(self):
        """Should return comprehensive user stats."""
        self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="STRESSED",
            actual="NEUTRAL",
            score=75.0,
        )
        
        stats = self.learner.get_user_stats("test_user")
        
        self.assertIn("adapter", stats)
        self.assertIn("experience_buffer_unused", stats)
        self.assertIn("experience_buffer_total", stats)
        self.assertEqual(stats["experience_buffer_total"], 1)
        self.assertEqual(stats["experience_buffer_unused"], 1)

    def test_update_accuracy(self):
        """Should track per-user accuracy."""
        self.learner.update_accuracy("test_user", 0.75)
        adapter = self.learner.get_adapter("test_user")
        self.assertEqual(adapter["accuracy"], 0.75)

    def test_adapter_persistence(self):
        """Adapter should persist across instances."""
        self.learner.update_from_feedback(
            user_id="test_user",
            features=self.sample_features,
            predicted="STRESSED",
            actual="NEUTRAL",
            score=75.0,
        )
        
        # Create new instance with same DB
        learner2 = OnlineLearner(db_dir=self.tmpdir)
        adapter = learner2.get_adapter("test_user")
        
        self.assertLess(adapter["threshold_adjustment"], 0.0)
        self.assertEqual(adapter["n_updates"], 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for LSTM + Online Learning."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.learner = OnlineLearner(db_dir=self.tmpdir)
        self.lstm = StressLSTM(hidden_size=16, num_layers=1, dropout=0.1)
        self.sample_features = {
            "hold_time_mean": 120.0,
            "hold_time_std": 25.0,
            "typing_speed_wpm": 45.0,
            "error_rate": 0.12,
        }

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_online_learning_improves_over_time(self):
        """Multiple corrections should improve adapter accuracy."""
        user_id = "test_user"
        
        # Simulate pattern: model predicts STRESSED, user is actually NEUTRAL
        for _ in range(10):
            self.learner.update_from_feedback(
                user_id=user_id,
                features=self.sample_features,
                predicted="STRESSED",
                actual="NEUTRAL",
                score=75.0,
            )
        
        adapter = self.learner.get_adapter(user_id)
        
        # Threshold should be significantly negative
        self.assertLess(adapter["threshold_adjustment"], -10.0)
        
        # Applying adapter should reduce score
        adjusted_score, _ = self.learner.apply_adapter(
            user_id=user_id,
            score=75.0,
            probabilities={"NEUTRAL": 0.2, "MILD": 0.3, "STRESSED": 0.5},
        )
        self.assertLess(adjusted_score, 75.0)

    def test_full_correction_loop(self):
        """Complete feedback → adapter → adjusted prediction loop."""
        user_id = "test_user"
        
        # 1. Model predicts STRESSED
        raw_score = 75.0
        raw_probs = {"NEUTRAL": 0.15, "MILD": 0.25, "STRESSED": 0.60}
        
        # 2. User corrects: actually NEUTRAL
        self.learner.update_from_feedback(
            user_id=user_id,
            features=self.sample_features,
            predicted="STRESSED",
            actual="NEUTRAL",
            score=raw_score,
        )
        
        # 3. Next prediction should be adjusted
        adjusted_score, adjusted_probs = self.learner.apply_adapter(
            user_id=user_id,
            score=raw_score,
            probabilities=raw_probs,
        )
        
        # Score should decrease
        self.assertLess(adjusted_score, raw_score)
        
        # NEUTRAL probability should increase
        self.assertGreater(adjusted_probs["NEUTRAL"], raw_probs["NEUTRAL"])


import numpy as np


if __name__ == "__main__":
    unittest.main()
