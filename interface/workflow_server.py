# interface/workflow_server.py

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from core_os import update_manager
from core_os import provisioning
from control.os_control import write_control, read_control
from state.os_state import read_state

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPDATES_DIR = os.path.join(BASE_DIR, "updates", "incoming")
APPS_DIR = os.path.join(BASE_DIR, "apps", "incoming")
CONTROL_DIR = os.path.join(BASE_DIR, "control")
SAFE_MODE_FLAG = os.path.join(CONTROL_DIR, "SAFE_MODE")


def _normalized_filename(filename):
    if not isinstance(filename, str):
        return None
    cleaned = os.path.basename(filename.strip())
    if not cleaned or cleaned in (".", ".."):
        return None
    if cleaned != filename.strip():
        return None
    return cleaned


def _set_safe_mode(enabled):
    control = read_control()
    control["safe_mode"] = bool(enabled)
    write_control(control)

    if enabled:
        os.makedirs(CONTROL_DIR, exist_ok=True)
        with open(SAFE_MODE_FLAG, "w") as f:
            f.write("1")
    else:
        try:
            os.remove(SAFE_MODE_FLAG)
        except FileNotFoundError:
            pass


def _read_body(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length <= 0:
        return b""
    return handler.rfile.read(length)


def _send_json(handler, payload, status=200):
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class WorkflowHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            device = provisioning.read_device_identity()
            state = read_state()
            payload = {
                "device": device,
                "current_mode": state.get("current_mode"),
                "boot_phase": state.get("boot_phase"),
                "updates": {
                    "current_slot": update_manager.current_slot(),
                    "pending_slot": update_manager.pending_slot(),
                    "incoming": update_manager.list_incoming_updates()
                }
            }
            return _send_json(self, payload)

        if self.path == "/apps":
            try:
                files = os.listdir(APPS_DIR)
            except Exception:
                files = []
            return _send_json(self, {"apps": files})

        return _send_json(self, {"error": "not_found"}, status=404)

    def do_POST(self):
        if self.path == "/upload":
            filename = _normalized_filename(self.headers.get("X-File-Name"))
            target = self.headers.get("X-Target", "apps")
            if not filename:
                return _send_json(self, {"error": "missing_filename"}, status=400)

            data = _read_body(self)
            if target == "updates":
                os.makedirs(UPDATES_DIR, exist_ok=True)
                dest = os.path.join(UPDATES_DIR, filename)
            else:
                os.makedirs(APPS_DIR, exist_ok=True)
                dest = os.path.join(APPS_DIR, filename)

            with open(dest, "wb") as f:
                f.write(data)
            return _send_json(self, {"saved": filename, "target": target})

        if self.path == "/update/apply":
            payload = {}
            try:
                payload = json.loads(_read_body(self).decode("utf-8"))
            except Exception:
                payload = {}
            filename = _normalized_filename(payload.get("filename"))
            expected = payload.get("sha256")
            if not filename:
                return _send_json(self, {"error": "missing_filename"}, status=400)
            try:
                slot = update_manager.apply_incoming_update(filename, expected_sha256=expected)
                return _send_json(self, {"staged_slot": slot})
            except Exception as exc:
                return _send_json(self, {"error": str(exc)}, status=400)

        if self.path == "/provision":
            payload = {}
            try:
                payload = json.loads(_read_body(self).decode("utf-8"))
            except Exception:
                payload = {}
            ssid = payload.get("ssid")
            psk = payload.get("psk")
            label = payload.get("label")
            if label:
                provisioning.set_device_label(label)
            if ssid or psk:
                provisioning.set_network_config(ssid=ssid, psk=psk, source="workflow")
            provisioning.mark_provisioned()
            return _send_json(self, {"ok": True})

        if self.path == "/safe-mode":
            payload = {}
            try:
                payload = json.loads(_read_body(self).decode("utf-8"))
            except Exception:
                payload = {}
            enabled = bool(payload.get("enabled"))
            _set_safe_mode(enabled)
            return _send_json(self, {"safe_mode": enabled})

        if self.path == "/control":
            payload = {}
            try:
                payload = json.loads(_read_body(self).decode("utf-8"))
            except Exception:
                payload = {}
            control = read_control()
            for key, value in payload.items():
                control[key] = value
            write_control(control)
            return _send_json(self, {"ok": True})

        return _send_json(self, {"error": "not_found"}, status=404)

    def log_message(self, format, *args):
        return


def run(host="0.0.0.0", port=8080):
    server = HTTPServer((host, port), WorkflowHandler)
    server.serve_forever()


if __name__ == "__main__":
    run()
