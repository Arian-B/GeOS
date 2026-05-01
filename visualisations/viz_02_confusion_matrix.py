import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (confusion_matrix, classification_report,
                              accuracy_score, balanced_accuracy_score)
from sklearn.model_selection import train_test_split

plt.rcParams['figure.facecolor'] = '#0B1B18'
plt.rcParams['axes.facecolor'] = '#0F2922'
plt.rcParams['text.color'] = '#E6FFF2'
plt.rcParams['axes.labelcolor'] = '#E6FFF2'
plt.rcParams['xtick.color'] = '#E6FFF2'
plt.rcParams['ytick.color'] = '#E6FFF2'

import sys
sys.path.insert(0, ".")
from ml_engine.policy_features import feature_columns

df = pd.read_csv("datasets/telemetry.csv").dropna(subset=['os_mode'])
X = df[feature_columns()]
y = df['os_mode']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = joblib.load("ml_engine/policy_model.pkl")
y_pred = model.predict(X_test)

acc = accuracy_score(y_test, y_pred)
bal_acc = balanced_accuracy_score(y_test, y_pred)
print(f"\nAccuracy:          {acc:.4f}")
print(f"Balanced Accuracy: {bal_acc:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Confusion matrix
cm = confusion_matrix(y_test, y_pred, labels=["BALANCED","ENERGY_SAVER","PERFORMANCE"])
cm_pct = cm.astype(float) / cm.sum(axis=1)[:, np.newaxis] * 100

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle(f"GeOS LightGBM Policy Model — Confusion Matrix\n"
             f"Accuracy: {acc:.4f} | Balanced Accuracy: {bal_acc:.4f}",
             fontsize=14, color='#E6FFF2', fontweight='bold')

# Raw counts
sns.heatmap(cm, annot=True, fmt='d', ax=axes[0],
            xticklabels=["BALANCED","ENERGY_SAVER","PERFORMANCE"],
            yticklabels=["BALANCED","ENERGY_SAVER","PERFORMANCE"],
            cmap='YlGn', linewidths=1, linecolor='#082E28')
axes[0].set_title("Raw Counts", color='#E6FFF2')
axes[0].set_xlabel("Predicted Label")
axes[0].set_ylabel("True Label")

# Percentage
sns.heatmap(cm_pct, annot=True, fmt='.1f', ax=axes[1],
            xticklabels=["BALANCED","ENERGY_SAVER","PERFORMANCE"],
            yticklabels=["BALANCED","ENERGY_SAVER","PERFORMANCE"],
            cmap='YlGn', linewidths=1, linecolor='#082E28')
axes[1].set_title("Percentage per True Class (%)", color='#E6FFF2')
axes[1].set_xlabel("Predicted Label")
axes[1].set_ylabel("True Label")

plt.tight_layout()
plt.savefig("viz_02_confusion_matrix.png", dpi=150, bbox_inches='tight')
plt.show()
print("Saved: viz_02_confusion_matrix.png")
