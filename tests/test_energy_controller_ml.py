import unittest
from unittest import mock

from core_os import energy_controller


class EnergyControllerMLTests(unittest.TestCase):
    def test_safety_override_wins_over_model_prediction(self):
        data = {
            "battery": 8,
            "soil_moisture": 50,
            "temperature": 24,
        }
        control = {"mode": "AUTO"}

        with mock.patch.object(
            energy_controller,
            "predict_policy",
            return_value={
                "mode": "PERFORMANCE",
                "confidence": 0.99,
                "source": "LIGHTGBM",
                "top_features": [],
            },
        ), mock.patch.object(
            energy_controller,
            "current_thresholds",
            return_value={
                "battery_energy_saver": 15,
                "soil_performance": 31,
                "temperature_energy_saver": 34,
            },
        ):
            decision = energy_controller.evaluate_control_decision(
                data=data,
                control=control,
                policy_features={},
                current_mode=energy_controller.BALANCED,
                mode_lock_counter=0,
            )

        self.assertEqual(decision["new_mode"]["name"], "ENERGY_SAVER")
        self.assertEqual(decision["policy_source"], "SAFETY_OVERRIDE")
        self.assertIn("safety_override", decision["ml_reason_codes"])
        self.assertEqual(decision["ml_confidence_source"], "MODEL_PROBABILITY")

    def test_manual_override_wins_when_safe(self):
        data = {
            "battery": 90,
            "soil_moisture": 55,
            "temperature": 24,
        }
        control = {
            "mode": "MANUAL",
            "manual_override_mode": "PERFORMANCE",
            "forced_mode": "PERFORMANCE",
        }

        with mock.patch.object(
            energy_controller,
            "predict_policy",
            return_value={
                "mode": "BALANCED",
                "confidence": 0.8,
                "source": "LIGHTGBM",
                "top_features": [],
            },
        ), mock.patch.object(
            energy_controller,
            "current_thresholds",
            return_value={
                "battery_energy_saver": 15,
                "soil_performance": 31,
                "temperature_energy_saver": 34,
            },
        ):
            decision = energy_controller.evaluate_control_decision(
                data=data,
                control=control,
                policy_features={},
                current_mode=energy_controller.BALANCED,
                mode_lock_counter=0,
            )

        self.assertEqual(decision["new_mode"]["name"], "PERFORMANCE")
        self.assertEqual(decision["policy_source"], "MANUAL_OVERRIDE")
        self.assertIn("manual_override", decision["ml_reason_codes"])

    def test_mode_lock_prevents_non_safety_switch(self):
        data = {
            "battery": 90,
            "soil_moisture": 55,
            "temperature": 24,
        }
        control = {"mode": "AUTO"}

        with mock.patch.object(
            energy_controller,
            "predict_policy",
            return_value={
                "mode": "PERFORMANCE",
                "confidence": 0.9,
                "source": "LIGHTGBM",
                "top_features": [],
            },
        ), mock.patch.object(
            energy_controller,
            "current_thresholds",
            return_value={
                "battery_energy_saver": 15,
                "soil_performance": 31,
                "temperature_energy_saver": 34,
            },
        ):
            decision = energy_controller.evaluate_control_decision(
                data=data,
                control=control,
                policy_features={},
                current_mode=energy_controller.BALANCED,
                mode_lock_counter=2,
            )

        self.assertEqual(decision["new_mode"]["name"], "BALANCED")
        self.assertIn("mode_lock", decision["ml_reason_codes"])

    def test_confidence_metadata_passes_through_from_policy(self):
        data = {
            "battery": 90,
            "soil_moisture": 55,
            "temperature": 24,
        }
        control = {"mode": "AUTO"}

        with mock.patch.object(
            energy_controller,
            "predict_policy",
            return_value={
                "mode": "BALANCED",
                "confidence": 0.61,
                "raw_confidence": 0.85,
                "confidence_source": "CALIBRATED",
                "source": "LIGHTGBM",
                "top_features": [],
            },
        ), mock.patch.object(
            energy_controller,
            "current_thresholds",
            return_value={
                "battery_energy_saver": 15,
                "soil_performance": 31,
                "temperature_energy_saver": 34,
            },
        ):
            decision = energy_controller.evaluate_control_decision(
                data=data,
                control=control,
                policy_features={},
                current_mode=energy_controller.BALANCED,
                mode_lock_counter=0,
            )

        self.assertAlmostEqual(decision["ml_confidence"], 0.61, places=4)
        self.assertAlmostEqual(decision["ml_raw_confidence"], 0.85, places=4)
        self.assertEqual(decision["ml_confidence_source"], "CALIBRATED")


if __name__ == "__main__":
    unittest.main()
