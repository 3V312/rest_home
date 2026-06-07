import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

data = {
    '自理': {
        '有补贴': {'实际支出占比': 7.61, '理论刚需占比': 9.28},
        '无补贴': {'实际支出占比': 8.32, '理论刚需占比': 10.24}
    },
    '半失能': {
        '有补贴': {'实际支出占比': 15.56, '理论刚需占比': 18.45},
        '无补贴': {'实际支出占比': 16.18, '理论刚需占比': 19.34}
    },
    '失能': {
        '有补贴': {'实际支出占比': 15.75, '理论刚需占比': 18.47},
        '无补贴': {'实际支出占比': 16.03, '理论刚需占比': 18.94}
    }
}

elderly_types = ['自理', '半失能', '失能']

fig, ax = plt.subplots(figsize=(14, 6))

x = np.arange(len(elderly_types)) * 0.4
width = 0.08

bars1 = ax.bar(x - 1.5*width, [data[et]['有补贴']['实际支出占比'] for et in elderly_types], width, label='有补贴-实际支出', color='#4A90D9')
bars2 = ax.bar(x - 0.5*width, [data[et]['有补贴']['理论刚需占比'] for et in elderly_types], width, label='有补贴-理论刚需', color='#7EC8E3')
bars3 = ax.bar(x + 0.5*width, [data[et]['无补贴']['实际支出占比'] for et in elderly_types], width, label='无补贴-实际支出', color='#5D9B48')
bars4 = ax.bar(x + 1.5*width, [data[et]['无补贴']['理论刚需占比'] for et in elderly_types], width, label='无补贴-理论刚需', color='#A8D8A8')

ax.set_xlabel('老人类型')
ax.set_ylabel('支出占比(%)')
ax.set_xticks(x)
ax.set_xticklabels(elderly_types)

all_values = []
for et in elderly_types:
    all_values.extend([
        data[et]['有补贴']['实际支出占比'],
        data[et]['有补贴']['理论刚需占比'],
        data[et]['无补贴']['实际支出占比'],
        data[et]['无补贴']['理论刚需占比']
    ])
max_value = max(all_values)
ax.set_ylim(0, max_value + 5)

ax.legend(loc='upper left', frameon=False)

for bars in [bars1, bars2, bars3, bars4]:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}%',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),
                   textcoords="offset points",
                   ha='center', va='bottom', fontsize=7)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
os.makedirs('results', exist_ok=True)
output_path = f'results/fig_economic_accessibility_{timestamp}.png'
plt.tight_layout()
plt.savefig(output_path, dpi=300, facecolor='white')
print(f'图片已保存: {output_path}')
