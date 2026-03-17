import os
import unittest
from unittest import mock

from ml_engine import auto_trainer


class AutoTrainerTests(unittest.TestCase):
    def test_auto_trainer_can_be_disabled_by_env(self):
        with mock.patch.dict(os.environ, {"GEOS_DISABLE_AUTO_TRAINER": "1"}, clear=False):
            auto_trainer._trainer_started = False
            thread = auto_trainer.start_auto_trainer()
        self.assertIsNone(thread)
        self.assertFalse(auto_trainer._trainer_started)


if __name__ == "__main__":
    unittest.main()
