import unittest
from unittest.mock import patch

from ml_engine import infer_model
from ml_engine import policy_optimizer
from ml_engine import threshold_advisor
from ml_engine import train_policy_model


class MlHelperTests(unittest.TestCase):
    def test_predict_mode_uses_policy_output(self):
        with patch.object(infer_model, "predict_policy", return_value={"mode": "PERFORMANCE"}):
            self.assertEqual(infer_model.predict_mode({"battery": 80}), "PERFORMANCE")

    def test_predict_best_mode_returns_mode_and_confidence(self):
        with patch.object(
            policy_optimizer,
            "predict_policy",
            return_value={"mode": "ENERGY_SAVER", "confidence": 0.91},
        ):
            mode, confidence = policy_optimizer.predict_best_mode({"battery": 10})
        self.assertEqual(mode, "ENERGY_SAVER")
        self.assertEqual(confidence, 0.91)

    def test_threshold_advisor_merges_runtime_thresholds(self):
        with patch.object(
            threshold_advisor,
            "current_thresholds",
            return_value={"battery_energy_saver": 19, "soil_performance": 31},
        ), patch.object(
            threshold_advisor,
            "predict_policy",
            return_value={"mode": "BALANCED"},
        ):
            merged, mode = threshold_advisor.adjust_thresholds(
                {"soil_moisture": 40},
                {"battery_energy_saver": 25, "temperature_energy_saver": 38},
            )

        self.assertEqual(mode, "BALANCED")
        self.assertEqual(merged["battery_energy_saver"], 19)
        self.assertEqual(merged["soil_performance"], 31)
        self.assertEqual(merged["temperature_energy_saver"], 38)

    def test_load_lightgbm_params_falls_back_to_defaults_when_file_missing(self):
        with patch("ml_engine.train_policy_model.os.path.exists", return_value=False):
            params = train_policy_model.load_lightgbm_params()

        self.assertEqual(params["objective"], "multiclass")
        self.assertEqual(params["n_estimators"], train_policy_model.DEFAULT_LIGHTGBM_PARAMS["n_estimators"])


if __name__ == "__main__":
    unittest.main()
