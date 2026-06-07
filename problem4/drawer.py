import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patches as mpatches

categories = ['助餐', '日间照料', '上门护理', '康复理疗', '助浴', '紧急救助']
# 旧减新
data_diff = {
    '小型': [-0.67, -0.21, 0.07, 0.1, 0.085, 0.0],
    '中型': [-0.76, -0.23, 0.08, 0.01, -0.22, 0.0],
    '大型': [-0.76, -0.395, 0.17, 0.01, -0.05, 0.0]
}

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

fig, axes = plt.subplots(1, 3, figsize=(18, 6), subplot_kw=dict(polar=True))

min_limit = -0.8
max_limit = 0.3

for i, (ax, t) in enumerate(zip(axes, ['小型', '中型', '大型'])):
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False, dtype=float)
    diffs = np.array(data_diff[t], dtype=float)
    
    theta = np.linspace(0, 2 * np.pi, 100)
    
    # 绘制0参考圆（浅灰色虚线圆）
    ax.plot(theta, [0.001] * len(theta), color='gray', linestyle='--', linewidth=1, zorder=1)
    
    # 绘制从0指向数据点的短线段
    for j in range(len(angles)):
        color = 'red' if diffs[j] > 0 else ('green' if diffs[j] < 0 else 'gray')
        if diffs[j] != 0:
            ax.plot([angles[j], angles[j]], [0, diffs[j]], color=color, linewidth=2, zorder=5)
    
    # 绘制数据点（蓝色）和连接线（蓝色）
    for j in range(len(angles)):
        ax.scatter([angles[j]], [diffs[j]], color='blue', s=50, zorder=15)
        
        next_j = (j + 1) % len(angles)
        ax.plot([angles[j], angles[next_j]], [diffs[j], diffs[next_j]], color='blue', linewidth=1.5, alpha=0.8, zorder=10)
        
        # 标注数值
        if diffs[j] != 0:
            label_pos = diffs[j] + 0.02 if diffs[j] > 0 else diffs[j] - 0.02
            va = 'bottom' if diffs[j] > 0 else 'top'
            ax.text(angles[j], label_pos, f'{diffs[j]:+.2f}', ha='center', va=va, fontsize=8, fontweight='bold')

    ax.set_xticks(angles)
    ax.set_xticklabels(categories)
    ax.set_title(t, y=-0.1)

    ax.set_ylim(min_limit, max_limit)
    ax.set_yticks([-0.8, -0.6, -0.4, -0.2, 0, 0.2, 0.3])
    ax.set_yticklabels(['-0.8', '-0.6', '-0.4', '-0.2', '0', '0.2', '0.3'])

    ax.set_rlabel_position(45)

legend_elements = [
    Line2D([0], [0], color='blue', lw=2, marker='o', label='数值'),
    Line2D([0], [0], color='red', lw=2, label='调高'),
    Line2D([0], [0], color='green', lw=2, label='调低')
]
fig.legend(handles=legend_elements, loc='lower left', ncol=3, frameon=False)

plt.tight_layout()
plt.show()
