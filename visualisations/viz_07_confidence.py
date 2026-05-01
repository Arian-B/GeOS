import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import sys
sys.path.insert(0, ".")
from ml_engine.policy_features import feature_columns

plt.rcParams['figure.facecolor'] = '#0B1B18'
plt.rcParams['axes.facecolor'] = '#0F2922'
plt.rcParams['text.color'] = '#E6FFF2'
plt.rcParams['axes.labelcolor'] = '#E6FFF2'
plt.rcParams['xtick.color'] = '#E6FFF2'
plt.rcParams['ytick.color'] = '#E6FFF2'

df = pd.read_csv("datasets/telemetry.csv").dropna(subset=['os_mode'])
X = df[feature_columns()]
y = df['os_mode']

_, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

model = joblib.load("ml_engine/policy_model.pkl")
proba = model.predict_proba(X_test)
max_proba = proba.max(axis=1)
preds = model.predict(X_test)
correct = (preds == y_test.values)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("GeOS LightGBM — Prediction Confidence Distribution",
             fontsize=14, color='#E6FFF2', fontweight='bold')

# Overall confidence
axes[0].hist(max_proba, bins=50, color='#1B7F6A', edgecolor='#082E28', linewidth=0.5)
axes[0].axvline(max_proba.mean(), color='#E0B34A', lw=2,
                label=f'Mean: {max_proba.mean():.3f}')
axes[0].axvline(np.median(max_proba), color='#E67E80', lw=2,
                label=f'Median: {np.median(max_proba):.3f}')
axes[0].set_title("Overall Confidence Distribution")
axes[0].set_xlabel("Max Class Probability")
axes[0].set_ylabel("Count")
axes[0].legend(facecolor='#0F2922', edgecolor='#1D6658')
for spine in axes[0].spines.values():
    spine.set_color('#1D6658')

# Correct vs incorrect
axes[1].hist(max_proba[correct], bins=40, color='#74C69D', alpha=0.7,
             label=f'Correct ({correct.sum():,})', edgecolor='#082E28')
axes[1].hist(max_proba[~correct], bins=40, color='#E67E80', alpha=0.7,
             label=f'Incorrect ({(~correct).sum():,})', edgecolor='#082E28')
axes[1].set_title("Confidence: Correct vs Incorrect Predictions")
axes[1].set_xlabel("Max Class Probability")
axes[1].set_ylabel("Count")
axes[1].legend(facecolor='#0F2922', edgecolor='#1D6658')
for spine in axes[1].spines.values():
    spine.set_color('#1D6658')

plt.tight_layout()
plt.savefig("viz_07_confidence_distribution.png", dpi=150, bbox_inches='tight')
plt.show()
high_conf = (max_proba > 0.9).sum() / len(max_proba) * 100
print(f"High confidence (>90%): {high_conf:.1f}% of predictions")
print("Saved: viz_07_confidence_distribution.png")
