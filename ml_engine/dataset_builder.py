import json
import os

try:
    import pandas as pd
except Exception:
    pd = None

from ml_engine.policy_features import PolicyFeatureBuilder, feature_columns


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "datasets", "telemetry_log.jsonl")
CSV_FILE = os.path.join(BASE_DIR, "datasets", "telemetry.csv")


def _require_pandas():
    if pd is None:
        raise RuntimeError("pandas is required to build the training dataset")


def _iter_records(raw_path=RAW_FILE):
    with open(raw_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                yield record


def build(raw_path=RAW_FILE, csv_path=CSV_FILE):
    _require_pandas()

    if not os.path.exists(raw_path):
        raise FileNotFoundError(raw_path)

    builder = PolicyFeatureBuilder()
    rows = []

    for record in _iter_records(raw_path):
        builder.add_snapshot(record)
        feature_row = builder.current_features()
        if not feature_row:
            continue

        row = {name: feature_row.get(name) for name in feature_columns()}
        row["os_mode"] = record.get("os_mode")
        row["timestamp"] = record.get("timestamp")
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["os_mode"])

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df.to_csv(csv_path, index=False)

    print(f"[DATASET] Built dataset with {len(df)} rows")
    print(f"[DATASET] Saved to {csv_path}")
    return df


if __name__ == "__main__":
    build()
