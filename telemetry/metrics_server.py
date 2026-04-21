# telemetry/metrics_server.py

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE_DIR, "state", "os_state.json")
PERF_FILE = os.path.join(BASE_DIR, "logs", "performance_metrics.json")


def _read_json(path, default):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except Exception:
        return default


def _send_json(handler, payload, status=200):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/metrics", "/health"):
            state = _read_json(STATE_FILE, {})
            perf = _read_json(PERF_FILE, {})
            payload = {
                "state": state,
                "performance": perf
            }
            return _send_json(self, payload)
        return _send_json(self, {"error": "not_found"}, status=404)

    def log_message(self, format, *args):
        return


def run(host="0.0.0.0", port=8090):
    server = HTTPServer((host, port), MetricsHandler)
    server.serve_forever()


if __name__ == "__main__":
    run()
