import warnings
warnings.filterwarnings('ignore', message='.*feature names.*')
warnings.filterwarnings('ignore', message='.*FitFailedWarning.*')
warnings.filterwarnings('ignore', category=UserWarning)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import learning_curve, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from lightgbm import LGBMClassifier
import sys
sys.path.insert(0, ".")
from ml_engine.policy_features import feature_columns
from ml_engine.train_policy_model import load_lightgbm_params

plt.rcParams['figure.facecolor'] = '#0B1B18'
plt.rcParams['axes.facecolor'] = '#0F2922'
plt.rcParams['text.color'] = '#E6FFF2'
plt.rcParams['axes.labelcolor'] = '#E6FFF2'
plt.rcParams['xtick.color'] = '#E6FFF2'
plt.rcParams['ytick.color'] = '#E6FFF2'

df = pd.read_csv("datasets/telemetry.csv").dropna(subset=['os_mode'])
X = df[feature_columns()]
y = df['os_mode']

params = load_lightgbm_params()
# Explicitly set num_class so LightGBM never guesses from fold data
params = dict(params)
params['num_class'] = 3

pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('model', LGBMClassifier(**params))
])

# Use StratifiedKFold explicitly to guarantee all 3 classes in every fold
# Start at 0.3 (not 0.1) because BALANCED is only ~5.9% — too few at 10%
cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

print("Computing learning curve (this may take a few minutes)...")
train_sizes, train_scores, val_scores = learning_curve(
    pipeline, X, y,
    train_sizes=np.linspace(0.3, 1.0, 7),   # start from 30% for class safety
    cv=cv,
    scoring='accuracy',
    n_jobs=1,
    verbose=1,
    error_score=0.0    # score failed folds as 0 instead of crashing
)

train_mean = train_scores.mean(axis=1)
train_std  = train_scores.std(axis=1)
val_mean   = val_scores.mean(axis=1)
val_std    = val_scores.std(axis=1)

fig, ax = plt.subplots(figsize=(12, 8))
fig.suptitle("GeOS LightGBM — Learning Curve\n"
             "(Training size vs Accuracy, StratifiedKFold CV=3)",
             fontsize=14, color='#E6FFF2', fontweight='bold')

ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std,
                alpha=0.2, color='#74C69D', label='Training ± std')
ax.fill_between(train_sizes, val_mean - val_std, val_mean + val_std,
                alpha=0.2, color='#E0B34A', label='Validation ± std')
ax.plot(train_sizes, train_mean, 'o-', color='#74C69D', lw=2.5, ms=8,
        label=f'Training Accuracy (max={train_mean.max():.4f})')
ax.plot(train_sizes, val_mean, 's-', color='#E0B34A', lw=2.5, ms=8,
        label=f'Validation Accuracy (max={val_mean.max():.4f})')

for ts, tm, vm in zip(train_sizes, train_mean, val_mean):
    ax.text(ts, tm + 0.003, f'{tm:.3f}', ha='center', color='#74C69D', fontsize=8.5, fontweight='bold')
    ax.text(ts, vm - 0.013, f'{vm:.3f}', ha='center', color='#E0B34A', fontsize=8.5, fontweight='bold')

ax.set_xlabel("Training Set Size (rows)")
ax.set_ylabel("Accuracy Score")
ax.set_ylim(0.78, 1.04)
ax.legend(facecolor='#0F2922', edgecolor='#1D6658', loc='lower right')
ax.grid(True, alpha=0.12, color='#1D6658')
for spine in ax.spines.values():
    spine.set_color('#1D6658')

plt.tight_layout(rect=[0, 0, 1, 0.93])  # leave room for 2-line suptitle
plt.savefig("viz_10_learning_curve.png", dpi=150, bbox_inches='tight')
plt.show()
print(f"\nFinal validation accuracy:  {val_mean[-1]:.4f}")
print(f"Final training accuracy:    {train_mean[-1]:.4f}")
print(f"Gap (overfitting measure):  {train_mean[-1] - val_mean[-1]:.4f}")
print("Saved: viz_10_learning_curve.png")

