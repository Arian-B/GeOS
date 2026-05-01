import json
import matplotlib.pyplot as plt

plt.rcParams['figure.facecolor'] = '#0B1B18'
plt.rcParams['axes.facecolor'] = '#0F2922'
plt.rcParams['text.color'] = '#E6FFF2'
plt.rcParams['axes.labelcolor'] = '#E6FFF2'
plt.rcParams['xtick.color'] = '#E6FFF2'
plt.rcParams['ytick.color'] = '#E6FFF2'

with open("ml_engine/rolling_backtest_report.json") as f:
    data = json.load(f)

windows = data['windows']
window_ids = [f"W{w['window']}\n({w['train_rows']}→{w['test_rows']})" for w in windows]
acc = [w['accuracy'] for w in windows]
bal_acc = [w['balanced_accuracy'] for w in windows]
macro_f1 = [w['macro_f1'] for w in windows]

fig, ax = plt.subplots(figsize=(12, 6))
fig.suptitle("GeOS LightGBM — Rolling Temporal Backtest\n"
             f"Avg Accuracy: {data['average_accuracy']:.4f} | "
             f"Avg Balanced Acc: {data['average_balanced_accuracy']:.4f} | "
             f"Avg Macro F1: {data['average_macro_f1']:.4f}",
             fontsize=13, color='#E6FFF2', fontweight='bold')

ax.plot(window_ids, acc, 'o-', color='#74C69D', lw=2.5, ms=10, label='Accuracy')
ax.plot(window_ids, bal_acc, 's-', color='#E0B34A', lw=2.5, ms=10, label='Balanced Accuracy')
ax.plot(window_ids, macro_f1, '^-', color='#E67E80', lw=2.5, ms=10, label='Macro F1')

for i, (a, b, f) in enumerate(zip(acc, bal_acc, macro_f1)):
    ax.text(i, a + 0.005, f'{a:.3f}', ha='center', color='#74C69D', fontsize=9)
    ax.text(i, b - 0.015, f'{b:.3f}', ha='center', color='#E0B34A', fontsize=9)
    ax.text(i, f - 0.025, f'{f:.3f}', ha='center', color='#E67E80', fontsize=9)

ax.axhline(y=data['average_accuracy'], color='#74C69D', linestyle='--', alpha=0.4)
ax.axhline(y=data['average_balanced_accuracy'], color='#E0B34A', linestyle='--', alpha=0.4)

ax.set_ylim(0.5, 1.05)
ax.set_xlabel("Backtest Window (train rows → test rows)")
ax.set_ylabel("Score")
ax.legend(facecolor='#0F2922', edgecolor='#1D6658')
for spine in ax.spines.values():
    spine.set_color('#1D6658')

plt.tight_layout()
plt.savefig("viz_06_rolling_backtest.png", dpi=150, bbox_inches='tight')
plt.show()
print("Saved: viz_06_rolling_backtest.png")
