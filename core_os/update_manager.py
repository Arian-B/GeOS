# core_os/update_manager.py

import datetime
import hashlib
import hmac
import json
import os
import shutil
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(BASE_DIR, "system")
SLOTS_DIR = os.path.join(SYSTEM_DIR, "slots")
INCOMING_DIR = os.path.join(BASE_DIR, "updates", "incoming")
STATE_DIR = os.path.join(BASE_DIR, "state")
BOOT_SUCCESS_FILE = os.path.join(STATE_DIR, "boot_success.flag")
POLICY_FILE = os.path.join(STATE_DIR, "update_policy.json")
KEYS_FILE = os.path.join(STATE_DIR, "update_keys.json")

CURRENT_FILE = os.path.join(SYSTEM_DIR, "slot_current")
LAST_GOOD_FILE = os.path.join(SYSTEM_DIR, "slot_last_good")
PENDING_FILE = os.path.join(SYSTEM_DIR, "slot_pending.json")
PROTECTED_FILE = os.path.join(SYSTEM_DIR, "protected_paths.json")

DEFAULT_POLICY = {
    "require_signature": False,
    "require_sha256": False,
    "enforce_when_present": True,
    "auto_stage_updates": True,
    "auto_apply_updates": False
}


def _read_text(path):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return None


def _write_text(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(str(value))


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


def read_policy():
    data = _read_json(POLICY_FILE, DEFAULT_POLICY.copy())
    if not isinstance(data, dict):
        data = DEFAULT_POLICY.copy()
    changed = False
    for k, v in DEFAULT_POLICY.items():
        if k not in data:
            data[k] = v
            changed = True
    if changed:
        _write_json(POLICY_FILE, data)
    return data


def read_keys():
    data = _read_json(KEYS_FILE, {})
    return data if isinstance(data, dict) else {}


def _ensure_layout():
    os.makedirs(SLOTS_DIR, exist_ok=True)
    os.makedirs(INCOMING_DIR, exist_ok=True)
    for slot in ("a", "b"):
        os.makedirs(os.path.join(SLOTS_DIR, f"slot_{slot}"), exist_ok=True)
    if _read_text(CURRENT_FILE) is None:
        _write_text(CURRENT_FILE, "a")
    if _read_text(LAST_GOOD_FILE) is None:
        _write_text(LAST_GOOD_FILE, _read_text(CURRENT_FILE))


def _protected_paths():
    default = {
        "protected": [
            "core_os",
            "gui",
            "control",
            "state",
            "logs",
            "datasets",
            "ml_engine",
            "telemetry",
            "workloads",
            "sensors",
            "interface"
        ]
    }
    data = _read_json(PROTECTED_FILE, default)
    if not data.get("protected"):
        data = default
    return set(data.get("protected", []))


def current_slot():
    _ensure_layout()
    return _read_text(CURRENT_FILE) or "a"


def other_slot(slot_name=None):
    slot_name = slot_name or current_slot()
    return "b" if slot_name == "a" else "a"


def pending_slot():
    data = _read_json(PENDING_FILE, {})
    return data.get("slot")


def handle_boot(prev_boot_ok=None):
    _ensure_layout()
    pending = _read_json(PENDING_FILE, {})
    pending_slot_name = pending.get("slot")
    if pending_slot_name:
        if prev_boot_ok is None:
            prev_boot_ok = os.path.exists(BOOT_SUCCESS_FILE)
        if prev_boot_ok:
            _write_text(CURRENT_FILE, pending_slot_name)
            _write_text(LAST_GOOD_FILE, pending_slot_name)
        else:
            last_good = _read_text(LAST_GOOD_FILE) or "a"
            _write_text(CURRENT_FILE, last_good)
        try:
            os.remove(PENDING_FILE)
        except FileNotFoundError:
            pass


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_signature(path):
    try:
        with open(path, "r") as f:
            content = f.read().strip()
    except Exception:
        return None
    if not content:
        return None
    if content.startswith("{"):
        try:
            data = json.loads(content)
            return data.get("hmac_sha256") or data.get("signature")
        except Exception:
            return None
    return content


def verify_sha256(zip_path, expected_sha256=None, sha256_path=None):
    expected = expected_sha256
    if expected is None and sha256_path:
        try:
            with open(sha256_path, "r") as f:
                expected = f.read().strip()
        except Exception:
            expected = None
    if expected is None:
        raise ValueError("SHA256 required but not provided")
    actual = _hash_file(zip_path)
    if actual.lower() != expected.lower():
        raise ValueError("SHA256 mismatch for update package")
    return True


def verify_hmac(zip_path, signature_path, hmac_key):
    if not signature_path:
        raise ValueError("Signature required but not provided")
    if not hmac_key:
        raise ValueError("HMAC key missing")
    signature = _read_signature(signature_path)
    if not signature:
        raise ValueError("Signature required but missing")
    computed = hmac.new(
        str(hmac_key).encode("utf-8"),
        digestmod=hashlib.sha256
    )
    with open(zip_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            computed.update(chunk)
    digest = computed.hexdigest()
    if not hmac.compare_digest(digest.lower(), signature.lower()):
        raise ValueError("Signature verification failed")
    return True


def _validate_zip(zip_path):
    protected = _protected_paths()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError("Unsafe path in update package")
            top = name.split("/")[0]
            if top in protected:
                raise ValueError(f"Update attempts to overwrite protected path: {top}")


def _clear_dir(path):
    if os.path.isdir(path):
        for entry in os.listdir(path):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                shutil.rmtree(full, ignore_errors=True)
            else:
                try:
                    os.remove(full)
                except Exception:
                    pass


def stage_update(zip_path, expected_sha256=None):
    _ensure_layout()
    if not os.path.exists(zip_path):
        raise FileNotFoundError(zip_path)

    if expected_sha256:
        actual = _hash_file(zip_path)
        if actual.lower() != expected_sha256.lower():
            raise ValueError("SHA256 mismatch for update package")

    _validate_zip(zip_path)

    target_slot = other_slot()
    target_dir = os.path.join(SLOTS_DIR, f"slot_{target_slot}")
    _clear_dir(target_dir)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)

    pending = {
        "slot": target_slot,
        "package": os.path.basename(zip_path),
        "staged_at": datetime.datetime.now().isoformat(timespec="seconds")
    }
    _write_json(PENDING_FILE, pending)
    return target_slot


def stage_update_with_policy(zip_path, signature_path=None, sha256_path=None, expected_sha256=None):
    policy = read_policy()
    keys = read_keys()
    require_sig = bool(policy.get("require_signature"))
    require_sha = bool(policy.get("require_sha256"))
    enforce_when_present = bool(policy.get("enforce_when_present", True))

    if require_sha or (enforce_when_present and (expected_sha256 or sha256_path)):
        verify_sha256(zip_path, expected_sha256=expected_sha256, sha256_path=sha256_path)
    if require_sig or (enforce_when_present and signature_path):
        verify_hmac(zip_path, signature_path=signature_path, hmac_key=keys.get("hmac_key"))

    return stage_update(zip_path, expected_sha256=expected_sha256)


def list_incoming_updates():
    _ensure_layout()
    try:
        return [f for f in os.listdir(INCOMING_DIR) if f.lower().endswith(".zip")]
    except Exception:
        return []


def apply_incoming_update(filename, expected_sha256=None):
    path = os.path.join(INCOMING_DIR, filename)
    base = os.path.splitext(filename)[0]
    sig_path = os.path.join(INCOMING_DIR, base + ".sig")
    if not os.path.exists(sig_path):
        sig_path = os.path.join(INCOMING_DIR, base + ".sig.json")
        if not os.path.exists(sig_path):
            sig_path = None
    sha_path = os.path.join(INCOMING_DIR, base + ".sha256")
    if not os.path.exists(sha_path):
        sha_path = None
    return stage_update_with_policy(
        path,
        signature_path=sig_path,
        sha256_path=sha_path,
        expected_sha256=expected_sha256
    )
