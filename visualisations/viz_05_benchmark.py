import json
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['figure.facecolor'] = '#0B1B18'
plt.rcParams['axes.facecolor'] = '#0F2922'
plt.rcParams['text.color'] = '#E6FFF2'
plt.rcParams['axes.labelcolor'] = '#E6FFF2'
plt.rcParams['xtick.color'] = '#E6FFF2'
plt.rcParams['ytick.color'] = '#E6FFF2'

with open("ml_engine/benchmark_results.json") as f:
    data = json.load(f)

results = [r for r in data['results'] if 'error' not in r]
models = [r['model'] for r in results]
accuracy = [r['accuracy'] for r in results]
bal_accuracy = [r['balanced_accuracy'] for r in results]
macro_f1 = [r['macro_f1'] for r in results]
train_sec = [r['train_seconds'] for r in results]
pred_ms = [r['predict_ms_per_row'] for r in results]

x = np.arange(len(models))
width = 0.26
colors = ['#74C69D', '#1B7F6A', '#E0B34A', '#E67E80', '#9EC7BB']

fig, axes = plt.subplots(1, 3, figsize=(18, 7))
fig.suptitle("GeOS ML Model Benchmark — Stratified 5-Fold Cross-Validation\n"
             f"Dataset: {data['rows_total']:,} rows",
             fontsize=14, color='#E6FFF2', fontweight='bold')

# Accuracy comparison
for i, (model, acc, bal, f1, c) in enumerate(zip(models, accuracy, bal_accuracy, macro_f1, colors)):
    axes[0].bar(i - width, acc, width, color=c, alpha=0.9, label=model)
    axes[0].bar(i, bal, width, color=c, alpha=0.6)
    axes[0].bar(i + width, f1, width, color=c, alpha=0.4)

axes[0].set_xticks(x)
axes[0].set_xticklabels(models, rotation=20, ha='right', fontsize=9)
axes[0].set_ylim(0.65, 1.02)
axes[0].set_ylabel("Score")
axes[0].set_title("Accuracy / Balanced Acc / Macro F1\n(dark=Acc, mid=BalAcc, light=F1)")
axes[0].axhline(y=0.95, color='#E67E80', linestyle='--', alpha=0.5, label='95% line')
for spine in axes[0].spines.values():
    spine.set_color('#1D6658')

# Training time
bars = axes[1].bar(models, train_sec, color=colors, edgecolor='#1D6658')
axes[1].set_title("Training Time (seconds)")
axes[1].set_ylabel("Seconds")
axes[1].set_xticklabels(models, rotation=20, ha='right', fontsize=9)
for bar, val in zip(bars, train_sec):
    axes[1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 f'{val:.2f}s', ha='center', color='#E6FFF2', fontsize=9)
for spine in axes[1].spines.values():
    spine.set_color('#1D6658')

# Inference speed
bars2 = axes[2].bar(models, pred_ms, color=colors, edgecolor='#1D6658')
axes[2].set_title("Inference Speed (ms per row)")
axes[2].set_ylabel("Milliseconds")
axes[2].set_xticklabels(models, rotation=20, ha='right', fontsize=9)
for bar, val in zip(bars2, pred_ms):
    axes[2].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.0002,
                 f'{val:.4f}', ha='center', color='#E6FFF2', fontsize=8)
for spine in axes[2].spines.values():
    spine.set_color('#1D6658')

plt.tight_layout()
plt.savefig("viz_05_benchmark_comparison.png", dpi=150, bbox_inches='tight')
plt.show()
print("Saved: viz_05_benchmark_comparison.png")
