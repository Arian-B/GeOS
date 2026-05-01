import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams['figure.facecolor'] = '#0B1B18'
plt.rcParams['axes.facecolor'] = '#0F2922'
plt.rcParams['text.color'] = '#E6FFF2'
plt.rcParams['axes.labelcolor'] = '#E6FFF2'
plt.rcParams['xtick.color'] = '#E6FFF2'
plt.rcParams['ytick.color'] = '#E6FFF2'

df = pd.read_csv("datasets/telemetry.csv").dropna(subset=['os_mode', 'timestamp'])
df['timestamp'] = pd.to_datetime(df['timestamp'])
df = df.sort_values('timestamp')

# Sample last 2000 rows for readability
sample = df.tail(2000).copy()

mode_map = {'ENERGY_SAVER': 0, 'BALANCED': 1, 'PERFORMANCE': 2}
color_map = {'ENERGY_SAVER': '#74C69D', 'BALANCED': '#E6FFF2', 'PERFORMANCE': '#E0B34A'}
sample['mode_num'] = sample['os_mode'].map(mode_map)

fig, axes = plt.subplots(3, 1, figsize=(16, 10), sharex=True)
fig.suptitle("GeOS System — OS Mode & Sensor Timeline (Last 2000 observations)",
             fontsize=14, color='#E6FFF2', fontweight='bold')

# Mode timeline
for mode, color in color_map.items():
    mask = sample['os_mode'] == mode
    axes[0].scatter(sample.loc[mask, 'timestamp'], sample.loc[mask, 'mode_num'],
                    c=color, s=5, alpha=0.8, label=mode)
axes[0].set_yticks([0, 1, 2])
axes[0].set_yticklabels(['ENERGY_SAVER', 'BALANCED', 'PERFORMANCE'])
axes[0].set_title("OS Energy Mode Over Time")
axes[0].legend(facecolor='#0F2922', edgecolor='#1D6658', loc='upper right', markerscale=3)
for spine in axes[0].spines.values():
    spine.set_color('#1D6658')

# Battery
if 'battery' in sample.columns:
    axes[1].plot(sample['timestamp'], sample['battery'],
                 color='#E0B34A', lw=0.8, alpha=0.9)
    axes[1].axhline(25, color='#E67E80', lw=1.5, linestyle='--', label='Safety threshold (25%)')
    axes[1].set_title("Battery Level (%)")
    axes[1].set_ylabel("%")
    axes[1].legend(facecolor='#0F2922', edgecolor='#1D6658')
    for spine in axes[1].spines.values():
        spine.set_color('#1D6658')

# Soil + Temperature
ax2 = axes[2]
if 'soil_moisture' in sample.columns:
    ax2.plot(sample['timestamp'], sample['soil_moisture'],
             color='#74C69D', lw=0.8, alpha=0.9, label='Soil Moisture (%)')
    ax2.axhline(35, color='#74C69D', lw=1.5, linestyle='--', alpha=0.5)
ax3 = ax2.twinx()
ax3.tick_params(colors='#E6FFF2')
if 'temperature' in sample.columns:
    ax3.plot(sample['timestamp'], sample['temperature'],
             color='#E67E80', lw=0.8, alpha=0.9, label='Temperature (°C)')
ax2.set_title("Soil Moisture & Temperature Over Time")
ax2.set_ylabel("Soil Moisture %", color='#74C69D')
ax3.set_ylabel("Temperature °C", color='#E67E80')
ax2.legend(loc='upper left', facecolor='#0F2922', edgecolor='#1D6658')
ax3.legend(loc='upper right', facecolor='#0F2922', edgecolor='#1D6658')
for spine in ax2.spines.values():
    spine.set_color('#1D6658')

axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
plt.xticks(rotation=30, ha='right')
plt.tight_layout()
plt.savefig("viz_08_mode_timeline.png", dpi=150, bbox_inches='tight')
plt.show()
print("Saved: viz_08_mode_timeline.png")
