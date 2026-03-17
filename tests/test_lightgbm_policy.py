import json
import os
import tempfile
import unittest
from unittest import mock
import numpy as np

from ml_engine import lightgbm_policy


class LightGBMPolicyTests(unittest.TestCase):
    def test_load_lightgbm_params_merges_defaults_with_saved_params(self):
        with tempfile.TemporaryDirectory() as tmp:
            params_file = os.path.join(tmp, "lightgbm_params.json")
            with open(params_file, "w") as f:
                json.dump({"n_estimators": 300, "num_leaves": 63}, f)

            with mock.patch.object(lightgbm_policy, "BASE_DIR", tmp):
                pass

            from ml_engine import train_policy_model

            with mock.patch.object(train_policy_model, "LIGHTGBM_PARAMS_FILE", params_file):
                params = train_policy_model.load_lightgbm_params()

            self.assertEqual(params["n_estimators"], 300)
            self.assertEqual(params["num_leaves"], 63)
            self.assertEqual(params["objective"], "multiclass")

    def test_current_thresholds_merge_defaults_with_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta_file = os.path.join(tmp, "policy_model.meta.json")
            with open(meta_file, "w") as f:
                json.dump(
                    {
                        "model_type": "LightGBMClassifier",
                        "recommended_thresholds": {
                            "battery_energy_saver": 18,
                            "soil_performance": 30,
                        },
                    },
                    f,
                )

            with mock.patch.object(lightgbm_policy, "META_FILE", meta_file):
                lightgbm_policy._meta = None
                thresholds = lightgbm_policy.current_thresholds()

            self.assertEqual(thresholds["battery_energy_saver"], 18)
            self.assertEqual(thresholds["soil_performance"], 30)
            self.assertEqual(thresholds["temperature_energy_saver"], 38)

    def test_predict_policy_rejects_non_lightgbm_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta_file = os.path.join(tmp, "policy_model.meta.json")
            with open(meta_file, "w") as f:
                json.dump({"model_type": "NotLightGBM"}, f)

            with mock.patch.object(lightgbm_policy, "META_FILE", meta_file):
                lightgbm_policy._meta = None
                result = lightgbm_policy.predict_policy({"cpu_percent": 10})

            self.assertEqual(result["source"], "INVALID_MODEL_ARTIFACT")
            self.assertEqual(result["mode"], "BALANCED")

    def test_predict_policy_applies_confidence_calibrator(self):
        class FakeModel:
            def predict(self, frame):
                return ["PERFORMANCE"]

            def predict_proba(self, frame):
                return [[0.05, 0.1, 0.85]]

        class FakeCalibrator:
            def predict(self, values):
                return [0.61 for _ in values]

        with tempfile.TemporaryDirectory() as tmp:
            meta_file = os.path.join(tmp, "policy_model.meta.json")
            with open(meta_file, "w") as f:
                json.dump({"model_type": "LightGBMClassifier"}, f)

            with mock.patch.object(lightgbm_policy, "META_FILE", meta_file):
                lightgbm_policy._meta = None
                with mock.patch.object(lightgbm_policy, "load_model", return_value=FakeModel()):
                    with mock.patch.object(lightgbm_policy, "load_calibrator", return_value=FakeCalibrator()):
                        result = lightgbm_policy.predict_policy({"cpu_percent": 10})

        self.assertEqual(result["source"], "LIGHTGBM")
        self.assertEqual(result["mode"], "PERFORMANCE")
        self.assertAlmostEqual(result["raw_confidence"], 0.85, places=4)
        self.assertAlmostEqual(result["confidence"], 0.61, places=4)
        self.assertEqual(result["confidence_source"], "CALIBRATED")

    def test_predict_policy_uses_local_feature_contributions_when_available(self):
        class FakeImputer:
            def transform(self, frame):
                return frame

        class FakeBooster:
            def predict(self, frame, pred_contrib=False):
                if pred_contrib:
                    return np.array([[0.1, 0.6, -0.2, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
                raise AssertionError("unexpected booster predict")

        class FakeEstimator:
            classes_ = ["BALANCED", "PERFORMANCE"]
            booster_ = FakeBooster()

        class FakePipeline:
            named_steps = {
                "imputer": FakeImputer(),
                "model": FakeEstimator(),
            }

            def predict(self, frame):
                return ["BALANCED"]

            def predict_proba(self, frame):
                return [[0.8, 0.2]]

        with tempfile.TemporaryDirectory() as tmp:
            meta_file = os.path.join(tmp, "policy_model.meta.json")
            with open(meta_file, "w") as f:
                json.dump({"model_type": "LightGBMClassifier"}, f)

            with mock.patch.object(lightgbm_policy, "META_FILE", meta_file):
                lightgbm_policy._meta = None
                with mock.patch.object(lightgbm_policy, "load_model", return_value=FakePipeline()):
                    with mock.patch.object(lightgbm_policy, "load_calibrator", return_value=None):
                        with mock.patch.object(lightgbm_policy, "feature_names", return_value=["f1", "f2", "f3", "f4"]):
                            result = lightgbm_policy.predict_policy({"f1": 1, "f2": 2, "f3": 3, "f4": 4})

        self.assertEqual(result["top_features"][0]["feature"], "f2")
        self.assertEqual(result["top_features"][0]["direction"], "supports_prediction")
        self.assertAlmostEqual(result["top_features"][0]["contribution"], 0.6, places=4)


if __name__ == "__main__":
    unittest.main()
