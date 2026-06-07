import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def gen_plots():
    file_path = r"D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem1\results\1_0522_1617.xlsx"
    base_dir = os.path.dirname(file_path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(base_dir, f"image_{ts}")
    os.makedirs(out_dir, exist_ok=True)

    df1 = pd.read_excel(file_path, sheet_name='1.1人口预测')
    df2 = pd.read_excel(file_path, sheet_name='1.2理论需求')
    df3 = pd.read_excel(file_path, sheet_name='1.3实际需求')

    df1['Year'] = df1['年份'].str.extract(r'(\d+)').astype(int)
    fig, ax = plt.subplots(figsize=(8, 5))

    morandi_colors = [
        '#8E9AAF', '#CBC0D3', '#EFD3D7', '#FEEAFA', '#DEE2FF',
        '#A3B18A', '#588157', '#3A5A40', '#D4A373', '#FAEDCD'
    ]

    for idx, (com, group) in enumerate(df1.groupby('小区')):
        group = group.sort_values('Year')
        ax.plot(group['Year'], group['总老人口' if '总老人口' in df1.columns else '总老人数'],
                marker='o', color=morandi_colors[idx % 10], label=com, linewidth=2)
        
        for _, row in group.iterrows():
            ax.annotate(f"{int(row['总老人口' if '总老人口' in df1.columns else '总老人数'])}", 
                       xy=(row['Year'], row['总老人口' if '总老人口' in df1.columns else '总老人数']),
                       xytext=(0, 8), textcoords='offset points',
                       fontsize=7, ha='center', fontweight='bold')

    ax.set_xlabel('年份', fontsize=10)
    ax.set_ylabel('总老人数', fontsize=10)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.set_xticklabels(['第1年末', '第2年末', '第3年末', '第4年末', '第5年末'])

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, linestyle='--', alpha=0.3)

    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', frameon=False)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "population_trend.png"), dpi=300, facecolor='w', bbox_inches='tight')
    plt.close()

    piv2 = df2.pivot(index='小区', columns='服务项目', values='总量理论需求')
    piv3 = df3.pivot(index='小区', columns='服务项目', values='总量实际需求')
    piv_diff = piv2 - piv3

    com_order = sorted(piv2.index.tolist())
    svc_order = df2['服务项目'].unique().tolist()

    piv2 = piv2.loc[com_order, svc_order]
    piv3 = piv3.loc[com_order, svc_order]
    piv_diff = piv_diff.loc[com_order, svc_order]

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(piv2, annot=True, fmt='.0f', cmap='Blues', ax=ax,
                annot_kws={'size': 8}, cbar_kws={'fraction': 0.046, 'pad': 0.04},
                square=True, linewidths=0.5, linecolor='white')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
    ax.set_xlabel('服务项目', fontsize=10)
    ax.set_ylabel('小区', fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "theory_heatmap.png"), dpi=300, facecolor='w', bbox_inches='tight')
    plt.close()

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(piv3, annot=True, fmt='.0f', cmap='Blues', ax=ax,
                annot_kws={'size': 8}, cbar_kws={'fraction': 0.046, 'pad': 0.04},
                square=True, linewidths=0.5, linecolor='white')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
    ax.set_xlabel('服务项目', fontsize=10)
    ax.set_ylabel('小区', fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "actual_heatmap.png"), dpi=300, facecolor='w', bbox_inches='tight')
    plt.close()

    fig, ax = plt.subplots(figsize=(8, 6))
    v_max = max(abs(piv_diff.min().min()), abs(piv_diff.max().max()), 1.0)
    sns.heatmap(piv_diff, annot=True, fmt='.0f', cmap='coolwarm', center=0, vmin=-v_max, vmax=v_max, ax=ax,
                annot_kws={'size': 8}, cbar_kws={'fraction': 0.046, 'pad': 0.04},
                square=True, linewidths=0.5, linecolor='white')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
    ax.set_xlabel('服务项目', fontsize=10)
    ax.set_ylabel('小区', fontsize=10)
    ax.set_title('理论-实际需求差异', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "diff_heatmap.png"), dpi=300, facecolor='w', bbox_inches='tight')
    plt.close()

    fig, axes = plt.subplots(2, 5, figsize=(14, 8))
    axes = axes.flatten()
    
    com_list = sorted(df1['小区'].unique())
    
    line_colors = {'自理人数': '#2ca02c', '半失能人数': '#ff7f0e', '失能人数': '#d62728'}
    
    all_values = []
    for com in com_list:
        com_data = df1[df1['小区'] == com]
        all_values.extend(com_data['自理人数'].tolist())
        all_values.extend(com_data['半失能人数'].tolist())
        all_values.extend(com_data['失能人数'].tolist())
    
    y_min = 0
    y_max = max(all_values) * 1.1
    
    for idx, com in enumerate(com_list):
        ax = axes[idx]
        com_data = df1[df1['小区'] == com].sort_values('Year')
        
        ax.plot(com_data['Year'], com_data['自理人数'], 
               marker='o', color=line_colors['自理人数'], linewidth=1.5, markersize=4)
        ax.plot(com_data['Year'], com_data['半失能人数'], 
               marker='s', color=line_colors['半失能人数'], linewidth=1.5, markersize=4)
        ax.plot(com_data['Year'], com_data['失能人数'], 
               marker='^', color=line_colors['失能人数'], linewidth=1.5, markersize=4)
        
        ax.set_title(f'小区{com}', fontsize=10, fontweight='bold')
        ax.set_xlim(0.8, 5.2)
        ax.set_ylim(y_min, y_max)
        ax.set_xticks([1, 2, 3, 4, 5])
        
        if idx >= 5:
            ax.set_xlabel('年份', fontsize=8)
            ax.set_xticklabels(['1', '2', '3', '4', '5'])
        else:
            ax.set_xticklabels([])
        
        if idx % 5 == 0:
            ax.set_ylabel('人数', fontsize=8)
        else:
            ax.set_yticklabels([])
        
        if idx == 0:
            ax.legend(['自理', '半失能', '失能'], fontsize=7, loc='upper left')
        
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    for idx in range(len(com_list), 10):
        axes[idx].axis('off')
    
    fig.suptitle('各小区三种老人人数变化趋势', fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "population_by_type.png"), dpi=300, facecolor='w', bbox_inches='tight')
    plt.close()


if __name__ == '__main__':
    gen_plots()