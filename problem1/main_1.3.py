import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from scipy.optimize import minimize
import config1 as cfg

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def read_data():
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    xlsx_files = [f for f in os.listdir(results_dir) if f.endswith('.xlsx') and f.startswith('1_')]
    if not xlsx_files:
        raise FileNotFoundError(f"未找到结果文件，请先运行 main.py 生成结果")
    xlsx_files.sort(reverse=True)
    path = os.path.join(results_dir, xlsx_files[0])
    df11 = pd.read_excel(path, sheet_name='1.1人口预测')
    df12 = pd.read_excel(path, sheet_name='1.2理论需求')
    df13 = pd.read_excel(path, sheet_name='1.3实际需求')
    return df11, df12, df13


def solve_les_for_group(q_theory, p, w, b_max):
    if np.sum(p * q_theory) <= b_max:
        return q_theory

    def obj(q):
        return np.sum(w * (q - q_theory) ** 2)

    cons = ({'type': 'ineq', 'fun': lambda q: b_max - np.sum(p * q)})
    bnds = [(0, None) for _ in range(len(p))]

    res = minimize(obj, q_theory, method='SLSQP', bounds=bnds, constraints=cons)
    if res.success:
        return res.x

    total_cost = np.sum(p * q_theory)
    return q_theory * (b_max / total_cost) if total_cost > 0 else np.zeros_like(q_theory)


def compute_metrics(df_theory, df_old, df_les):
    y_t = df_theory['总量理论需求'].values
    y_o = df_old['总量实际需求'].values
    y_l = df_les['总量实际需求'].values

    rmse_o = np.sqrt(np.mean((y_o - y_t) ** 2))
    rmse_l = np.sqrt(np.mean((y_l - y_t) ** 2))

    ssd_o = np.sum((y_o - y_t) ** 2)
    ssd_l = np.sum((y_l - y_t) ** 2)

    rigid_t = y_t * cfg.RIGID_RATIO
    sat_o = np.sum(np.minimum(y_o, rigid_t)) / np.sum(rigid_t) if np.sum(rigid_t) > 0 else 1.0
    sat_l = np.sum(np.minimum(y_l, rigid_t)) / np.sum(rigid_t) if np.sum(rigid_t) > 0 else 1.0

    return {
        'old': [rmse_o, ssd_o, sat_o],
        'les': [rmse_l, ssd_l, sat_l]
    }


def plot_heatmap_diff(df_old, df_les, out_dir):
    piv_old = df_old.pivot(index='小区', columns='服务项目', values='总量实际需求')
    piv_les = df_les.pivot(index='小区', columns='服务项目', values='总量实际需求')
    piv_diff = (piv_les - piv_old).reindex(columns=cfg.SVCS)

    fig, ax = plt.subplots(figsize=(8, 6))
    v = max(abs(piv_diff.min().min()), abs(piv_diff.max().max()), 1.0)
    sns.heatmap(piv_diff, annot=True, fmt='.0f', cmap='coolwarm', center=0, vmin=-v, vmax=v, ax=ax,
                annot_kws={'size': 9}, cbar_kws={'fraction': 0.046, 'pad': 0.04})
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right', fontsize=10)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0, fontsize=10)
    ax.set_xlabel('服务项目', fontsize=10)
    ax.set_ylabel('小区', fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "diff_heatmap_les_vs_old.png"), dpi=300, facecolor='w')
    plt.close()


def plot_cdf(df_theory, df_old, df_les, out_dir):
    fig, ax = plt.subplots(figsize=(8, 5))
    for df, label, color, style in zip([df_theory, df_old, df_les],
                                       ['理论需求', '旧实际需求', 'LES实际需求'],
                                       ['#8E9AAF', '#D4A373', '#588157'], ['-', '--', ':']):
        col = '总量理论需求' if '总量理论需求' in df.columns else '总量实际需求'
        vals = np.sort(df[col].values)
        p = np.arange(1, len(vals) + 1) / len(vals)
        ax.plot(vals, p, label=label, color=color, linewidth=2, linestyle=style)

    ax.set_xlabel('需求次数', fontsize=10)
    ax.set_ylabel('累积比例', fontsize=10)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(False)
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "demand_cdf.png"), dpi=300, facecolor='w')
    plt.close()


def main():
    df11, df12, df13 = read_data()
    p_arr = np.array([8, 16, 24, 23, 20, 8])
    w_arr = np.array([5, 3, 1, 2, 2, 15])

    f_s_arr = np.array(cfg.F_S)
    f_h_arr = np.array(cfg.F_H)
    f_d_arr = np.array(cfg.F_D)

    df5 = df11[df11['年份'].astype(str).str.contains('5')].set_index('小区')
    df12 = df12.sort_values(by=['小区', '服务项目']).reset_index(drop=True)
    df13 = df13.sort_values(by=['小区', '服务项目']).reset_index(drop=True)

    res_les = []

    for c in sorted(df5.index.unique()):
        c_str = str(c).strip()
        row_pop = df5.loc[c]

        s_count = float(row_pop['自理人数'])
        h_count = float(row_pop['半失能人数'])
        d_count = float(row_pop['失能人数'])

        inc = cfg.C_DATA[c_str][5]

        b_s = s_count * inc * cfg.LIMITS[0]
        b_h = h_count * inc * cfg.LIMITS[1]
        b_d = d_count * inc * cfg.LIMITS[2]

        q_t_s = s_count * f_s_arr
        q_t_h = h_count * f_h_arr
        q_t_d = d_count * f_d_arr

        q_a_s = solve_les_for_group(q_t_s, p_arr, w_arr, b_s)
        q_a_h = solve_les_for_group(q_t_h, p_arr, w_arr, b_h)
        q_a_d = solve_les_for_group(q_t_d, p_arr, w_arr, b_d)

        q_a_total = q_a_s + q_a_h + q_a_d

        for idx, s_name in enumerate(cfg.SVCS):
            res_les.append([c_str, s_name, math.ceil(q_a_total[idx])])

    df13_les = pd.DataFrame(res_les, columns=['小区', '服务项目', '总量实际需求']).sort_values(
        by=['小区', '服务项目']).reset_index(drop=True)
    m = compute_metrics(df12, df13, df13_les)

    print("| 指标           | 旧实际        | LES实际       |")
    print("|----------------|---------------|---------------|")
    print(f"| RMSE           | {m['old'][0]:<14.2f} | {m['les'][0]:<14.2f} |")
    print(f"| SSD            | {m['old'][1]:<14.2f} | {m['les'][1]:<14.2f} |")
    print(f"| 刚性满足率      | {m['old'][2]:<14.2%} | {m['les'][2]:<14.2%} |")

    path_dir = r"D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem1\results"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    df_metrics = pd.DataFrame({
        '指标': ['RMSE', 'SSD', '刚性满足率'],
        '旧实际': [m['old'][0], m['old'][1], f"{m['old'][2]:.2%}"],
        'LES实际': [m['les'][0], m['les'][1], f"{m['les'][2]:.2%}"]
    })

    with pd.ExcelWriter(os.path.join(path_dir, f"1_LES_{ts}.xlsx")) as w:
        df13_les.to_excel(w, sheet_name='1.3_LES实际需求', index=False)
        df13.to_excel(w, sheet_name='1.3_旧实际需求', index=False)
        df_metrics.to_excel(w, sheet_name='指标对比结果', index=False)

    plot_heatmap_diff(df13, df13_les, path_dir)
    plot_cdf(df12, df13, df13_les, path_dir)


if __name__ == '__main__':
    main()