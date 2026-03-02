import copy
import json
import tempfile
import unittest
from unittest import mock

from core_os import boot_manager


class BootManagerSafeModeTests(unittest.TestCase):
    def test_safe_mode_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            restore_file = f"{tmp}/safe_mode_restore.json"

            control_store = {
                "mode": "AUTO",
                "manual_override_mode": None,
                "forced_mode": None,
                "maintenance": False,
                "safe_mode": False,
                "workloads": {
                    "sensor": True,
                    "irrigation": False,
                    "camera": True,
                    "analytics": False,
                },
            }
            state_store = {
                "boot_phase": "READY",
                "boot_message": None,
                "recovery_mode": False,
            }

            def _read_control():
                return copy.deepcopy(control_store)

            def _write_control(value):
                control_store.clear()
                control_store.update(copy.deepcopy(value))

            def _read_state():
                return copy.deepcopy(state_store)

            def _write_state(value):
                state_store.clear()
                state_store.update(copy.deepcopy(value))

            with mock.patch.object(boot_manager, "SAFE_MODE_RESTORE_FILE", restore_file), \
                mock.patch.object(boot_manager, "read_control", side_effect=_read_control), \
                mock.patch.object(boot_manager, "write_control", side_effect=_write_control), \
                mock.patch.object(boot_manager, "read_state", side_effect=_read_state), \
                mock.patch.object(boot_manager, "write_state", side_effect=_write_state):

                boot_manager._apply_safe_mode(True, reason="SAFE_MODE")
                self.assertTrue(control_store["safe_mode"])
                self.assertTrue(control_store["maintenance"])
                self.assertEqual(control_store["mode"], "MANUAL")
                self.assertEqual(control_store["manual_override_mode"], "ENERGY_SAVER")
                self.assertEqual(control_store["forced_mode"], "ENERGY_SAVER")
                self.assertEqual(
                    control_store["workloads"],
                    {
                        "sensor": False,
                        "irrigation": False,
                        "camera": False,
                        "analytics": False,
                    },
                )
                self.assertTrue(state_store["recovery_mode"])

                with open(restore_file, "r") as f:
                    restore_payload = json.load(f)
                self.assertEqual(restore_payload["mode"], "AUTO")
                self.assertFalse(restore_payload["maintenance"])
                self.assertTrue(restore_payload["workloads"]["sensor"])
                self.assertFalse(restore_payload["workloads"]["irrigation"])

                boot_manager._apply_safe_mode(False)
                self.assertFalse(control_store["safe_mode"])
                self.assertFalse(control_store["maintenance"])
                self.assertEqual(control_store["mode"], "AUTO")
                self.assertIsNone(control_store["manual_override_mode"])
                self.assertIsNone(control_store["forced_mode"])
                self.assertEqual(
                    control_store["workloads"],
                    {
                        "sensor": True,
                        "irrigation": False,
                        "camera": True,
                        "analytics": False,
                    },
                )
                self.assertFalse(state_store["recovery_mode"])
                self.assertEqual(state_store["boot_phase"], "READY")

    def test_safe_mode_disable_recovers_workloads_without_restore(self):
        control_store = {
            "mode": "MANUAL",
            "manual_override_mode": "ENERGY_SAVER",
            "forced_mode": "ENERGY_SAVER",
            "maintenance": True,
            "safe_mode": False,
            "workloads": {
                "sensor": False,
                "irrigation": False,
                "camera": False,
                "analytics": False,
            },
        }
        state_store = {
            "boot_phase": "RECOVERY",
            "boot_message": "SAFE_MODE",
            "recovery_mode": True,
        }

        with mock.patch.object(boot_manager, "_read_json", return_value={}), \
            mock.patch.object(boot_manager, "read_control", side_effect=lambda: copy.deepcopy(control_store)), \
            mock.patch.object(boot_manager, "write_control", side_effect=lambda value: control_store.update(copy.deepcopy(value))), \
            mock.patch.object(boot_manager, "read_state", side_effect=lambda: copy.deepcopy(state_store)), \
            mock.patch.object(boot_manager, "write_state", side_effect=lambda value: state_store.update(copy.deepcopy(value))):
            boot_manager._apply_safe_mode(False)

        self.assertEqual(
            control_store["workloads"],
            {
                "sensor": True,
                "irrigation": True,
                "camera": True,
                "analytics": True,
            },
        )


if __name__ == "__main__":
    unittest.main()
