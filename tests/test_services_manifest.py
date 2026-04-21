import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "services" / "manifest.json"


class ServiceManifestTests(unittest.TestCase):
    def test_manifest_exists_and_is_non_empty(self):
        self.assertTrue(MANIFEST_PATH.exists())
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    def test_manifest_entries_have_required_fields(self):
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        names = set()
        modules = set()

        for entry in data:
            self.assertIn("name", entry)
            self.assertIn("module", entry)
            self.assertTrue(entry["name"])
            self.assertTrue(entry["module"])
            self.assertNotIn(entry["name"], names)
            self.assertNotIn(entry["module"], modules)
            names.add(entry["name"])
            modules.add(entry["module"])


if __name__ == "__main__":
    unittest.main()
