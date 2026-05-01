import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import label_binarize
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
classes = ["BALANCED", "ENERGY_SAVER", "PERFORMANCE"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

model = joblib.load("ml_engine/policy_model.pkl")
y_score = model.predict_proba(X_test)
y_test_bin = label_binarize(y_test, classes=classes)

colors = ['#74C69D', '#E0B34A', '#E67E80']
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("GeOS LightGBM — ROC Curves (One-vs-Rest, Multi-class)",
             fontsize=14, color='#E6FFF2', fontweight='bold')

# Individual class ROC curves
for i, (cls, color) in enumerate(zip(classes, colors)):
    fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_score[:, i])
    roc_auc = auc(fpr, tpr)
    axes[0].plot(fpr, tpr, color=color, lw=2,
                 label=f'{cls} (AUC = {roc_auc:.4f})')

axes[0].plot([0, 1], [0, 1], 'w--', lw=1, alpha=0.5, label='Random Classifier')
axes[0].set_xlim([0.0, 1.0])
axes[0].set_ylim([0.0, 1.05])
axes[0].set_xlabel('False Positive Rate')
axes[0].set_ylabel('True Positive Rate')
axes[0].set_title('Per-Class ROC Curves')
axes[0].legend(facecolor='#0F2922', edgecolor='#1D6658', loc='lower right')
for spine in axes[0].spines.values():
    spine.set_color('#1D6658')

# Macro-average ROC
all_fpr = np.unique(np.concatenate([roc_curve(y_test_bin[:, i], y_score[:, i])[0]
                                     for i in range(len(classes))]))
mean_tpr = np.zeros_like(all_fpr)
for i in range(len(classes)):
    fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_score[:, i])
    mean_tpr += np.interp(all_fpr, fpr, tpr)
mean_tpr /= len(classes)
macro_auc = auc(all_fpr, mean_tpr)

axes[1].fill_between(all_fpr, mean_tpr, alpha=0.3, color='#1B7F6A')
axes[1].plot(all_fpr, mean_tpr, color='#74C69D', lw=2.5,
             label=f'Macro-avg ROC (AUC = {macro_auc:.4f})')
axes[1].plot([0,1],[0,1],'w--', lw=1, alpha=0.5)
axes[1].set_xlabel('False Positive Rate')
axes[1].set_ylabel('True Positive Rate')
axes[1].set_title('Macro-Average ROC Curve')
axes[1].legend(facecolor='#0F2922', edgecolor='#1D6658', loc='lower right')
for spine in axes[1].spines.values():
    spine.set_color('#1D6658')

plt.tight_layout()
plt.savefig("viz_04_roc_curves.png", dpi=150, bbox_inches='tight')
plt.show()
print(f"Macro AUC: {macro_auc:.4f}")
print("Saved: viz_04_roc_curves.png")
