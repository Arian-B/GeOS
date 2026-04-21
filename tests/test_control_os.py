import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from control import os_control


class ControlStateTests(unittest.TestCase):
    def test_read_control_creates_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            control_path = Path(tmpdir) / "control.json"
            with patch.object(os_control, "CONTROL_FILE", str(control_path)):
                data = os_control.read_control()

            self.assertEqual(data["mode"], "AUTO")
            self.assertIn("workloads", data)
            self.assertTrue(control_path.exists())

    def test_read_control_backfills_legacy_and_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            control_path = Path(tmpdir) / "control.json"
            legacy = {
                "auto_mode": False,
                "mode_override": "PERFORMANCE",
                "workloads": {"sensor": False},
            }
            control_path.write_text(json.dumps(legacy), encoding="utf-8")

            with patch.object(os_control, "CONTROL_FILE", str(control_path)):
                data = os_control.read_control()

            self.assertEqual(data["mode"], "MANUAL")
            self.assertEqual(data["forced_mode"], "PERFORMANCE")
            self.assertEqual(data["manual_override_mode"], "PERFORMANCE")
            self.assertIn("camera", data["workloads"])
            self.assertIn("maintenance", data)


if __name__ == "__main__":
    unittest.main()
