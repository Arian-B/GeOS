import os
import threading
import time

from ml_engine.dataset_builder import RAW_FILE, build
from ml_engine.train_policy_model import train_from_dataframe


MIN_SAMPLES = 200
TRAIN_INTERVAL_SECONDS = 30 * 60

_last_mtime = 0.0
_trainer_started = False


def auto_trainer_enabled():
    value = str(os.getenv("GEOS_DISABLE_AUTO_TRAINER", "")).strip().lower()
    return value not in ("1", "true", "yes", "on")


def train_once():
    global _last_mtime

    if not os.path.exists(RAW_FILE):
        return False

    mtime = os.path.getmtime(RAW_FILE)
    if mtime == _last_mtime:
        return False

    df = build()
    if len(df) < MIN_SAMPLES:
        return False

    train_from_dataframe(df)
    _last_mtime = mtime
    return True


def _loop():
    while True:
        try:
            train_once()
        except Exception:
            pass
        time.sleep(TRAIN_INTERVAL_SECONDS)


def start_auto_trainer():
    global _trainer_started
    if not auto_trainer_enabled():
        return None
    if _trainer_started:
        return None

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    _trainer_started = True
    return thread
