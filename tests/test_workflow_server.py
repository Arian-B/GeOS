import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from interface import workflow_server


class WorkflowServerTests(unittest.TestCase):
    def test_normalized_filename_accepts_simple_names(self):
        self.assertEqual(workflow_server._normalized_filename("update.zip"), "update.zip")

    def test_normalized_filename_rejects_path_traversal(self):
        self.assertIsNone(workflow_server._normalized_filename("../update.zip"))
        self.assertIsNone(workflow_server._normalized_filename("/tmp/update.zip"))
        self.assertIsNone(workflow_server._normalized_filename("nested/update.zip"))

    def test_set_safe_mode_syncs_flag_and_control_state(self):
        writes = []
        with tempfile.TemporaryDirectory() as tmpdir:
            safe_mode_flag = Path(tmpdir) / "SAFE_MODE"

            def fake_write_control(control):
                writes.append(dict(control))

            with patch.object(workflow_server, "SAFE_MODE_FLAG", str(safe_mode_flag)), patch.object(
                workflow_server, "CONTROL_DIR", tmpdir
            ), patch.object(
                workflow_server, "read_control", return_value={"safe_mode": False}
            ), patch.object(
                workflow_server, "write_control", side_effect=fake_write_control
            ):
                workflow_server._set_safe_mode(True)
                self.assertTrue(safe_mode_flag.exists())
                self.assertTrue(writes[-1]["safe_mode"])

                workflow_server._set_safe_mode(False)
                self.assertFalse(safe_mode_flag.exists())
                self.assertFalse(writes[-1]["safe_mode"])


if __name__ == "__main__":
    unittest.main()
