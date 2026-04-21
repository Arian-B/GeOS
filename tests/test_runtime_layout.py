import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RuntimeLayoutTests(unittest.TestCase):
    def test_core_runtime_files_exist(self):
        required = [
            ROOT / "main.py",
            ROOT / "gui" / "app.py",
            ROOT / "gui" / "main_window.py",
            ROOT / "services" / "manifest.json",
            ROOT / "control" / "os_control.py",
            ROOT / "state",
            ROOT / "logs",
            ROOT / "updates" / "incoming",
        ]
        for path in required:
            self.assertTrue(path.exists(), f"Missing required runtime path: {path}")


if __name__ == "__main__":
    unittest.main()
