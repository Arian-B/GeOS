import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core_os import notifications


class NotificationTests(unittest.TestCase):
    def setUp(self):
        notifications.clear_alerts()

    def test_raise_alert_caps_in_memory_alert_buffer(self):
        with patch.object(notifications, "MAX_ACTIVE_ALERTS", 3), patch.object(
            notifications, "log_event"
        ):
            for idx in range(5):
                notifications.raise_alert("WARN", f"alert-{idx}")

        self.assertEqual(len(notifications.ACTIVE_ALERTS), 3)
        self.assertEqual(notifications.ACTIVE_ALERTS[0]["message"], "alert-2")
        self.assertEqual(notifications.ACTIVE_ALERTS[-1]["message"], "alert-4")

    def test_get_active_alerts_reads_event_log_when_memory_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "os_events.log"
            entries = [
                {"event": "INFO", "data": {"message": "ignore"}},
                {"event": "ALERT", "data": {"level": "CRITICAL", "message": "farm dry"}},
                {"event": "ALERT", "data": {"level": "WARN", "message": "battery low"}},
            ]
            log_path.write_text("\n".join(json.dumps(item) for item in entries), encoding="utf-8")

            with patch.object(notifications, "EVENT_LOG", str(log_path)):
                alerts = notifications.get_active_alerts(limit=2)

        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0]["message"], "battery low")
        self.assertEqual(alerts[1]["message"], "farm dry")


if __name__ == "__main__":
    unittest.main()
