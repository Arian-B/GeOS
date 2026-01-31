# ml_engine/evaluate_policies.py

import json
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "os_events.log")

rule_decisions = []
ml_decisions = []

with open(LOG_FILE, "r") as f:
    for line in f:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        event = entry.get("event")
        data = entry.get("data")

        # Rule-based decision (actual OS mode)
        if event == "MODE_CHANGE" and isinstance(data, str):
            rule_decisions.append(data)

        # ML suggestion
        if event == "ML_PREDICTION" and isinstance(data, dict):
            ml_decisions.append(data.get("suggested_mode"))

# Align lengths (only comparable points)
min_len = min(len(rule_decisions), len(ml_decisions))
rule_decisions = rule_decisions[:min_len]
ml_decisions = ml_decisions[:min_len]

print("Evaluation Results")
print("------------------")
print(f"Total comparable decisions: {min_len}")

matches = sum(
    1 for r, m in zip(rule_decisions, ml_decisions) if r == m
)

print(f"Matches: {matches}")
if min_len > 0:
    print(f"Agreement rate: {matches / min_len:.2f}")
else:
    print("Agreement rate: N/A")

print("\nRule-based distribution:", Counter(rule_decisions))
print("ML-based distribution:", Counter(ml_decisions))
