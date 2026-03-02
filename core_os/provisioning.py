# core_os/provisioning.py

import datetime
import json
import os
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(BASE_DIR, "state")
DEVICE_FILE = os.path.join(STATE_DIR, "device.json")
NETWORK_FILE = os.path.join(STATE_DIR, "network.json")


def _read_json(path, default):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else default
    except Exception:
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def ensure_device_identity():
    data = _read_json(DEVICE_FILE, {})
    if data.get("device_id"):
        return data

    device = {
        "device_id": str(uuid.uuid4()),
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "provisioned": False,
        "label": None
    }
    _write_json(DEVICE_FILE, device)
    return device


def read_device_identity():
    return _read_json(DEVICE_FILE, {})


def set_device_label(label):
    data = ensure_device_identity()
    data["label"] = label
    _write_json(DEVICE_FILE, data)
    return data


def mark_provisioned():
    data = ensure_device_identity()
    data["provisioned"] = True
    _write_json(DEVICE_FILE, data)
    return data


def read_network_config():
    return _read_json(NETWORK_FILE, {})


def set_network_config(ssid=None, psk=None, source="manual"):
    config = read_network_config()
    if ssid is not None:
        config["ssid"] = ssid
    if psk is not None:
        config["psk"] = psk
    config["source"] = source
    config["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    _write_json(NETWORK_FILE, config)
    return config
