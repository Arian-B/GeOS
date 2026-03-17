import unittest

from ml_engine.policy_features import PolicyFeatureBuilder, feature_columns


class PolicyFeatureBuilderTests(unittest.TestCase):
    def test_builds_expected_runtime_feature_vector(self):
        builder = PolicyFeatureBuilder(window_size=4)

        samples = [
            {
                "cpu_percent": 10,
                "load_avg": 0.1,
                "memory_percent": 20,
                "battery": 80,
                "soil_moisture": 45,
                "temperature": 24,
                "humidity": 60,
                "hour": 8,
                "network": "ONLINE",
                "control_auto": True,
                "control_manual": False,
                "maintenance_enabled": False,
                "safe_mode_enabled": False,
                "emergency_shutdown_enabled": False,
                "irrigation_enabled": True,
                "ventilation_enabled": False,
                "workload_sensor_enabled": True,
                "workload_irrigation_enabled": True,
                "workload_camera_enabled": False,
                "workload_analytics_enabled": False,
                "workload_enabled_count": 2,
                "workload_active_count": 1,
            },
            {
                "cpu_percent": 12,
                "load_avg": 0.2,
                "memory_percent": 21,
                "battery": 78,
                "soil_moisture": 40,
                "temperature": 25,
                "humidity": 59,
                "hour": 9,
                "network": "ONLINE",
                "control_auto": True,
                "control_manual": False,
                "maintenance_enabled": False,
                "safe_mode_enabled": False,
                "emergency_shutdown_enabled": False,
                "irrigation_enabled": True,
                "ventilation_enabled": True,
                "workload_sensor_enabled": True,
                "workload_irrigation_enabled": True,
                "workload_camera_enabled": True,
                "workload_analytics_enabled": False,
                "workload_enabled_count": 3,
                "workload_active_count": 2,
            },
            {
                "cpu_percent": 14,
                "load_avg": 0.3,
                "memory_percent": 22,
                "battery": 76,
                "soil_moisture": 34,
                "temperature": 36,
                "humidity": 58,
                "hour": 10,
                "network": "OFFLINE",
                "control_auto": False,
                "control_manual": True,
                "maintenance_enabled": True,
                "safe_mode_enabled": True,
                "emergency_shutdown_enabled": False,
                "irrigation_enabled": False,
                "ventilation_enabled": True,
                "workload_sensor_enabled": True,
                "workload_irrigation_enabled": False,
                "workload_camera_enabled": True,
                "workload_analytics_enabled": False,
                "workload_enabled_count": 2,
                "workload_active_count": 1,
            },
        ]

        for sample in samples:
            builder.add_snapshot(sample)

        features = builder.current_features()

        self.assertEqual(sorted(features.keys()), sorted(feature_columns()))
        self.assertEqual(features["battery"], 76.0)
        self.assertAlmostEqual(features["battery_avg"], 78.0)
        self.assertAlmostEqual(features["battery_delta"], -4.0)
        self.assertEqual(features["network_online"], 0)
        self.assertEqual(features["control_manual"], 1)
        self.assertEqual(features["maintenance_enabled"], 1)
        self.assertEqual(features["safe_mode_enabled"], 1)
        self.assertEqual(features["workload_camera_enabled"], 1)
        self.assertEqual(features["workload_irrigation_enabled"], 0)
        self.assertAlmostEqual(features["workload_enabled_count_avg"], 7 / 3)
        self.assertAlmostEqual(features["workload_enabled_count_delta"], 0.0)
        self.assertEqual(features["workload_active_count"], 1)
        self.assertEqual(features["soil_dry_streak"], 1)
        self.assertEqual(features["temp_high_streak"], 1)


if __name__ == "__main__":
    unittest.main()
