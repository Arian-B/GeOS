import json
import os
import tempfile
import unittest
from unittest import mock

from sensors.sensor_simulator import SensorState
import sensors.sensor_simulator as sensor_simulator


class SensorSimulatorTests(unittest.TestCase):
    def test_generates_simulated_values_when_sensor_workload_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            control_file = os.path.join(tmp, "control.json")
            override_file = os.path.join(tmp, "sensor_inputs.json")

            with open(control_file, "w") as f:
                json.dump({"workloads": {"sensor": True}}, f)

            # No overrides file content -> simulator should synthesize values.
            with open(override_file, "w") as f:
                json.dump({}, f)

            with mock.patch.object(sensor_simulator, "CONTROL_FILE", control_file), \
                mock.patch.object(sensor_simulator, "OVERRIDE_FILE", override_file):
                sensors = SensorState()
                sensors.update()
                values = sensors.read()

            self.assertIsNotNone(values["soil_moisture"])
            self.assertIsNotNone(values["humidity"])
            self.assertIsNotNone(values["temperature"])

    def test_returns_na_style_values_when_sensor_workload_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            control_file = os.path.join(tmp, "control.json")
            override_file = os.path.join(tmp, "sensor_inputs.json")

            with open(control_file, "w") as f:
                json.dump({"workloads": {"sensor": False}}, f)
            with open(override_file, "w") as f:
                json.dump({}, f)

            with mock.patch.object(sensor_simulator, "CONTROL_FILE", control_file), \
                mock.patch.object(sensor_simulator, "OVERRIDE_FILE", override_file):
                sensors = SensorState()
                sensors.update()
                values = sensors.read()

            self.assertIsNone(values["soil_moisture"])
            self.assertIsNone(values["humidity"])


if __name__ == "__main__":
    unittest.main()
