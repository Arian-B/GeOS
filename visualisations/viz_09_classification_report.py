import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_fscore_support
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
y_pred = model.predict(X_test)

classes = ["BALANCED", "ENERGY_SAVER", "PERFORMANCE"]
precision, recall, f1, support = precision_recall_fscore_support(
    y_test, y_pred, labels=classes
)

x = np.arange(len(classes))
width = 0.25
fig, ax = plt.subplots(figsize=(12, 7))
fig.suptitle("GeOS LightGBM — Per-Class Precision, Recall & F1 Score",
             fontsize=14, color='#E6FFF2', fontweight='bold')

b1 = ax.bar(x - width, precision, width, label='Precision', color='#74C69D', edgecolor='#082E28')
b2 = ax.bar(x, recall, width, label='Recall', color='#1B7F6A', edgecolor='#082E28')
b3 = ax.bar(x + width, f1, width, label='F1 Score', color='#E0B34A', edgecolor='#082E28')

for bars in [b1, b2, b3]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.005,
                f'{h:.3f}', ha='center', va='bottom', color='#E6FFF2', fontsize=10, fontweight='bold')

# Add support counts
for i, (cls, sup) in enumerate(zip(classes, support)):
    ax.text(i, -0.07, f'n={sup:,}', ha='center', color='#9EC7BB', fontsize=9)

ax.set_xticks(x)
ax.set_xticklabels(classes, fontsize=12)
ax.set_ylim(0, 1.12)
ax.set_ylabel("Score")
ax.set_xlabel("Energy Mode Class")
ax.axhline(0.95, color='#E67E80', linestyle='--', alpha=0.5, label='95% reference line')
ax.legend(facecolor='#0F2922', edgecolor='#1D6658', loc='lower right')
for spine in ax.spines.values():
    spine.set_color('#1D6658')

plt.tight_layout()
plt.savefig("viz_09_per_class_metrics.png", dpi=150, bbox_inches='tight')
plt.show()
print("Saved: viz_09_per_class_metrics.png")
