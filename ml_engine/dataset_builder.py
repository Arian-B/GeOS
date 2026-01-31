# ml_engine/dataset_builder.py
import json
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "datasets", "telemetry_log.jsonl")
CSV_FILE = os.path.join(BASE_DIR, "datasets", "telemetry.csv")

def build():
    records = []
    with open(RAW_FILE, "r") as f:
        for line in f:
            records.append(json.loads(line))

    df = pd.DataFrame(records)
    df.dropna(inplace=True)
    df.to_csv(CSV_FILE, index=False)

    print(f"[DATASET] Built dataset with {len(df)} samples")
    print(f"[DATASET] Saved to {CSV_FILE}")

if __name__ == "__main__":
    build()
