import hashlib
import tempfile
import unittest
import zipfile

from core_os import update_manager


class UpdateManagerTests(unittest.TestCase):
    def test_verify_sha256_accepts_valid_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = f"{tmp}/update.zip"
            with open(payload, "wb") as f:
                f.write(b"test-update")
            with open(payload, "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()

            self.assertTrue(update_manager.verify_sha256(payload, expected_sha256=digest))

    def test_verify_sha256_rejects_invalid_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = f"{tmp}/update.zip"
            with open(payload, "wb") as f:
                f.write(b"test-update")

            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                update_manager.verify_sha256(payload, expected_sha256="0" * 64)

    def test_validate_zip_rejects_unsafe_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = f"{tmp}/unsafe.zip"
            with zipfile.ZipFile(payload, "w") as zf:
                zf.writestr("../escape.txt", "x")

            with self.assertRaisesRegex(ValueError, "Unsafe path"):
                update_manager._validate_zip(payload)


if __name__ == "__main__":
    unittest.main()
