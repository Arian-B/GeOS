import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['figure.facecolor'] = '#0B1B18'
matplotlib.rcParams['axes.facecolor'] = '#0F2922'
matplotlib.rcParams['text.color'] = '#E6FFF2'
matplotlib.rcParams['axes.labelcolor'] = '#E6FFF2'
matplotlib.rcParams['xtick.color'] = '#E6FFF2'
matplotlib.rcParams['ytick.color'] = '#E6FFF2'

df = pd.read_csv("datasets/telemetry.csv")

print(f"Total rows: {len(df)}")
print(f"Feature columns: {len(df.columns) - 2}")
print(df['os_mode'].value_counts())
print("\nMissing values:\n", df.isnull().sum().sum())

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("GeOS Training Dataset Overview", fontsize=16, color='#E6FFF2', fontweight='bold')

# Bar chart
counts = df['os_mode'].value_counts()
colors = ['#74C69D', '#1B7F6A', '#E0B34A']
axes[0].bar(counts.index, counts.values, color=colors, edgecolor='#1D6658', linewidth=1.5)
axes[0].set_title("Class Distribution (Bar)", color='#E6FFF2')
axes[0].set_xlabel("OS Energy Mode")
axes[0].set_ylabel("Number of Samples")
for i, (k, v) in enumerate(counts.items()):
    axes[0].text(i, v + 100, str(v), ha='center', color='#E6FFF2', fontweight='bold')

# Pie chart
axes[1].pie(counts.values, labels=counts.index, colors=colors,
            autopct='%1.1f%%', startangle=140,
            textprops={'color': '#E6FFF2'},
            wedgeprops={'edgecolor': '#082E28', 'linewidth': 2})
axes[1].set_title("Class Distribution (Pie)", color='#E6FFF2')

plt.tight_layout()
plt.savefig("viz_01_dataset_distribution.png", dpi=150, bbox_inches='tight')
plt.show()
print("Saved: viz_01_dataset_distribution.png")
