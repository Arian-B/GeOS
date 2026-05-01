import json
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams['figure.facecolor'] = '#0B1B18'
plt.rcParams['axes.facecolor'] = '#0F2922'
plt.rcParams['text.color'] = '#E6FFF2'
plt.rcParams['axes.labelcolor'] = '#E6FFF2'
plt.rcParams['xtick.color'] = '#E6FFF2'
plt.rcParams['ytick.color'] = '#E6FFF2'

with open("datasets/feature_importance.json") as f:
    data = json.load(f)

df = pd.DataFrame(data).head(30)
df = df.sort_values("importance", ascending=True)

colors = ['#E0B34A' if i >= len(df)-5 else '#1B7F6A' for i in range(len(df))]

fig, ax = plt.subplots(figsize=(12, 10))
bars = ax.barh(df['feature'], df['importance'], color=colors, edgecolor='#1D6658')
ax.set_title("GeOS LightGBM — Top 30 Feature Importances",
             fontsize=15, color='#E6FFF2', fontweight='bold', pad=15)
ax.set_xlabel("Normalized Importance Score")
ax.set_ylabel("Feature Name")

for bar, val in zip(bars, df['importance']):
    ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height()/2,
            f'{val:.4f}', va='center', color='#E6FFF2', fontsize=8)

ax.axvline(x=df['importance'].mean(), color='#E67E80', linestyle='--',
           linewidth=1.5, label=f'Mean importance ({df["importance"].mean():.4f})')
ax.legend(facecolor='#0F2922', edgecolor='#1D6658')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
for spine in ax.spines.values():
    spine.set_color('#1D6658')

plt.tight_layout()
plt.savefig("viz_03_feature_importance.png", dpi=150, bbox_inches='tight')
plt.show()
print("Saved: viz_03_feature_importance.png")
