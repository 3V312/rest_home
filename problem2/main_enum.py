#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import time
import itertools
import os
import matplotlib.pyplot as plt
import numpy as np
from config2 import *

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def evaluate_configuration(config_tuple):
    """评价单个服务站配置（满意度驱动的动态分配）"""
    total_cost = sum(CONSTRUCTION_COST[s] for s in config_tuple)
    if total_cost > BUDGET_MAX:
        return None

    stations = {i: MAX_CAPACITY[s] for i, s in enumerate(config_tuple) if s > 0}
    if not stations:
        return None

    allocation = {i: [] for i in stations.keys()}

    for j in range(10):
        best_station = -1
        best_satisfaction = -1.0
        
        for i in stations.keys():
            d = DIST_MATRIX[j][i]
            if d <= SERVICE_RADIUS:
                s3 = calc_community_s3(j)
                sat = calc_satisfaction_dynamic(d, 0.0, s3)
                
                if sat > best_satisfaction:
                    best_satisfaction = sat
                    best_station = i

        if best_station != -1:
            allocation[best_station].append(j)

    for st_idx, comms in allocation.items():
        if not comms:
            return None

    max_iterations = 50
    converged = False

    for iteration in range(max_iterations):
        theoretical_demand = {i: 0.0 for i in stations.keys()}
        for st_idx, comms in allocation.items():
            for comm_idx in comms:
                theoretical_demand[st_idx] += DAILY_DEMAND[comm_idx]

        actual_loads = {}
        utilization = {}
        for st_idx in stations:
            cap = stations[st_idx]
            demand = theoretical_demand[st_idx]
            actual_loads[st_idx] = min(demand, cap)
            utilization[st_idx] = min(demand / cap, 1.0) if cap > 0 else 0.0

        new_allocation = {i: [] for i in stations.keys()}
        allocation_changed = False

        for j in range(10):
            best_station = -1
            best_satisfaction = -1.0
            
            for i in stations.keys():
                d = DIST_MATRIX[j][i]
                if d <= SERVICE_RADIUS:
                    s3 = calc_community_s3(j)
                    sat = calc_satisfaction_dynamic(d, utilization[i], s3)
                    
                    if sat > best_satisfaction:
                        best_satisfaction = sat
                        best_station = i

            if best_station != -1:
                new_allocation[best_station].append(j)

        for st_idx in stations:
            if len(new_allocation[st_idx]) == 0:
                return None
            
            if set(new_allocation[st_idx]) != set(allocation.get(st_idx, [])):
                allocation_changed = True

        allocation = new_allocation

        if not allocation_changed:
            converged = True
            break

    theoretical_demand = {i: 0.0 for i in stations.keys()}
    for st_idx, comms in allocation.items():
        for comm_idx in comms:
            theoretical_demand[st_idx] += DAILY_DEMAND[comm_idx]

    truncation_factors = {}
    actual_loads = {}
    utilization = {}
    for st_idx in stations:
        cap = stations[st_idx]
        demand = theoretical_demand[st_idx]
        if demand > cap and demand > 0:
            truncation_factors[st_idx] = cap / demand
        else:
            truncation_factors[st_idx] = 1.0
        actual_loads[st_idx] = min(demand, cap)
        utilization[st_idx] = min(demand / cap, 1.0) if cap > 0 else 0.0

    covered_elderly = 0
    total_satisfaction = 0.0

    for st_idx, comms in allocation.items():
        tf = truncation_factors[st_idx]
        
        for comm_idx in comms:
            d = DIST_MATRIX[comm_idx][st_idx]
            s3 = calc_community_s3(comm_idx)
            sat = calc_satisfaction_dynamic(d, utilization[st_idx], s3)
            
            actual_served = ELDERLY_POP[comm_idx] * tf
            covered_elderly += actual_served
            total_satisfaction += sat * actual_served

    coverage = covered_elderly / TOTAL_ELDERLY
    avg_satisfaction = total_satisfaction / covered_elderly if covered_elderly > 0 else 0.0

    capacity_penalty = 0.0
    for st_idx, load in actual_loads.items():
        if load > stations[st_idx]:
            capacity_penalty += (load - stations[st_idx]) * 0.05

    raw_score = 0.5 * coverage + 0.5 * avg_satisfaction - capacity_penalty
    raw_score = max(raw_score, 0.0)

    return {
        'config': config_tuple,
        'cost': total_cost,
        'allocation': allocation,
        'coverage': coverage,
        'satisfaction': avg_satisfaction,
        'score': raw_score,
        'actual_loads': actual_loads,
        'theoretical_demand': theoretical_demand,
        'truncation_factors': truncation_factors,
        'stations': stations,
        'capacity_penalty': capacity_penalty,
        'converged': converged
    }


def plot_pareto_front(pareto_front, best_res, out_dir):
    """绘制帕累托前沿图"""
    fig, ax = plt.subplots(figsize=(14, 8))

    all_coverage = [p[0] for p in pareto_front]
    all_satisfaction = [p[1] for p in pareto_front]

    ax.scatter(all_coverage, all_satisfaction, c='gray', s=20, alpha=0.5, label='所有可行解')

    pareto_cov = [p[0] for p in pareto_front]
    pareto_sat = [p[1] for p in pareto_front]
    ax.scatter(pareto_cov, pareto_sat, c='red', s=80, marker='o', label='帕累托前沿解', zorder=5)

    if best_res:
        ax.scatter([best_res['coverage']], [best_res['satisfaction']],
                   c='blue', s=200, marker='*', label=f'最优加权和解 (得分={best_res["score"]:.4f})',
                   edgecolors='darkblue', linewidths=2, zorder=6)

    ax.set_xlabel('服务覆盖率', fontsize=12)
    ax.set_ylabel('平均满意度', fontsize=12)
    ax.set_title('帕累托前沿分析', fontsize=14)
    ax.legend(frameon=False, loc='lower right')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0.8, 1.02)
    ax.set_ylim(0.6, 1.02)

    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "pareto_front.png"), dpi=300, facecolor='w', bbox_inches='tight')
    plt.close()


def plot_map(allocation, out_dir):
    """绘制服务站覆盖地图"""
    try:
        coords = mds_projection(DIST_MATRIX)

        fig, ax = plt.subplots(figsize=(14, 8))

        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
                  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788']

        for i, comm in enumerate(COMMUNITIES):
            ax.plot(coords[i, 0], coords[i, 1], 'o', markersize=12, color='gray', alpha=0.5)
            ax.text(coords[i, 0], coords[i, 1], comm, fontsize=11, ha='center', va='center', fontweight='bold')

        station_colors = {}
        color_idx = 0
        for st_idx, comms in allocation.items():
            color = colors[color_idx % len(colors)]
            station_colors[st_idx] = color

            ax.plot(coords[st_idx, 0], coords[st_idx, 1], '*', markersize=25,
                    color=color, markeredgecolor='black', markeredgewidth=2, label=f'站点 {COMMUNITIES[st_idx]}')

            circle = plt.Circle((coords[st_idx, 0], coords[st_idx, 1]),
                                SERVICE_RADIUS / 1000, fill=False, color=color,
                                linestyle='--', linewidth=2, alpha=0.6)
            ax.add_patch(circle)

            for comm_idx in comms:
                ax.plot([coords[st_idx, 0], coords[comm_idx, 0]],
                        [coords[st_idx, 1], coords[comm_idx, 1]],
                        '-', color=color, linewidth=2, alpha=0.4)

            color_idx += 1

        ax.set_xlabel('X坐标 (km)', fontsize=12)
        ax.set_ylabel('Y坐标 (km)', fontsize=12)
        ax.set_title('服务站覆盖地图 (MDS投影)', fontsize=14)
        ax.legend(frameon=False, loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "coverage_map.png"), dpi=300, facecolor='w', bbox_inches='tight')
        plt.close()

    except Exception as e:
        print(f"地图绘制失败: {e}")


def output_profit_and_satisfaction(best_res, out_dir):
    """输出详细的利润和满意度分析报告"""
    if not best_res:
        return

    config = best_res['config']
    allocation = best_res['allocation']
    station_loads = best_res.get('actual_loads', best_res.get('station_loads', {}))
    stations = best_res['stations']

    txt_path = os.path.join(out_dir, "enumerate_full_result.txt")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("枚举法求解结果详细分析\n")
        f.write("=" * 70 + "\n\n")

        f.write("【一、服务站年度利润分析】\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'站点':<8} {'类型':<6} {'年收入(元)':<15} {'年支出(元)':<15} {'年利润(元)':<15}\n")
        f.write("-" * 70 + "\n")

        total_revenue = 0
        total_expense = 0
        total_profit = 0

        for st_idx in sorted(allocation.keys()):
            comm_names = [COMMUNITIES[c] for c in allocation[st_idx]]
            station_type = config[st_idx]
            type_name = ['无', '小型', '中型', '大型'][station_type]
            
            revenue, expense, profit = calc_station_profit(
                st_idx, allocation[st_idx], allocation, 
                station_loads,
                stations
            )
            
            total_revenue += revenue
            total_expense += expense
            total_profit += profit
            
            f.write(f"{COMMUNITIES[st_idx]:<8} {type_name:<6} {revenue:<15,.0f} {expense:<15,.0f} {profit:<15,.0f}\n")

        f.write("-" * 70 + "\n")
        f.write(f"{'总计':<8} {'':<6} {total_revenue:<15,.0f} {total_expense:<15,.0f} {total_profit:<15,.0f}\n\n")

        f.write("【二、小区满意度分析】\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'小区':<8} {'服务站':<8} {'距离(m)':<10} {'距离满意度':<12} {'响应满意度':<12} {'价格满意度':<12} {'综合满意度':<12}\n")
        f.write("-" * 70 + "\n")

        for st_idx, comms in sorted(allocation.items()):
            utilization = station_loads[st_idx] / stations[st_idx] if stations[st_idx] > 0 else 0
            utilization = min(utilization, 1.0)
            for comm_idx in comms:
                d = DIST_MATRIX[comm_idx][st_idx]
                s1 = calc_s1(d)
                s2 = calc_s2(utilization)
                s3 = calc_community_s3(comm_idx)
                sat = W1 * s1 + W2 * s2 + W3 * s3
                f.write(f"{COMMUNITIES[comm_idx]:<8} {COMMUNITIES[st_idx]:<8} {d:<10} {s1:<11.4f} {s2:<11.4f} {s3:<11.4f} {sat:<11.4f}\n")
        
        f.write("\n")
        
        f.write("【三、全局指标】\n")
        f.write(f"服务覆盖率: {best_res['coverage'] * 100:.2f}%\n")
        f.write(f"平均满意度: {best_res['satisfaction']:.4f}\n")
        f.write(f"加权得分: {best_res['score']:.4f}\n")
    
    print(f"枚举法详细结果已保存至: {txt_path}")


def main():
    """枚举算法主函数"""
    start_time = time.time()
    valid_count = 0
    best_res = None
    best_score = -1.0
    pareto_front = []
    
    reject_budget = 0
    reject_capacity = 0
    reject_no_station = 0
    
    total_combos = 4 ** 10
    print(f"开始枚举，总组合数: {total_combos:,}")
    
    for idx, combo in enumerate(itertools.product(range(4), repeat=10)):
        res = evaluate_configuration(combo)
        
        if res is None:
            total_cost = sum(CONSTRUCTION_COST[s] for s in combo)
            if total_cost > BUDGET_MAX:
                reject_budget += 1
            elif not any(s > 0 for s in combo):
                reject_no_station += 1
            else:
                reject_capacity += 1
            continue
        
        valid_count += 1
        raw_score = res['score']
        
        is_dominated = False
        new_pareto = []
        for p in pareto_front:
            if p[0] >= res['coverage'] and p[1] >= res['satisfaction']:
                is_dominated = True
                new_pareto.append(p)
            elif res['coverage'] >= p[0] and res['satisfaction'] >= p[1]:
                pass
            else:
                new_pareto.append(p)
        
        if not is_dominated:
            new_pareto.append((res['coverage'], res['satisfaction'], combo, raw_score))
        pareto_front = new_pareto

        if raw_score > best_score:
            best_score = raw_score
            best_res = res
        
        if (idx + 1) % 100000 == 0:
            elapsed = time.time() - start_time
            progress = (idx + 1) / total_combos * 100
            print(f"进度: {progress:.1f}% ({idx+1:,}/{total_combos:,}), 有效解: {valid_count}, 耗时: {elapsed:.1f}s")

    run_time = time.time() - start_time
    out_dir = get_out_dir("enum")

    if pareto_front:
        pareto_front_sorted = sorted(pareto_front, key=lambda x: x[3], reverse=True)
        best_cov, best_sat, best_combo, best_raw_score = pareto_front_sorted[0]
        best_res = evaluate_configuration(best_combo)
        best_score = best_raw_score

    txt_path = os.path.join(out_dir, "enumerate_result.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=== 枚举法求解结果 ===\n")
        f.write(f"总耗时: {run_time:.2f} 秒\n")
        f.write(f"总组合数: {4 ** 10:,}\n")
        f.write(f"满足预算及容量的有效组合数: {valid_count}\n\n")
        
        f.write("【约束违反统计】\n")
        f.write(f"  - 超预算被拒: {reject_budget:,} ({reject_budget/total_combos*100:.2f}%)\n")
        f.write(f"  - 容量超载被拒: {reject_capacity:,} ({reject_capacity/total_combos*100:.2f}%)\n")
        f.write(f"  - 未建站被拒: {reject_no_station:,} ({reject_no_station/total_combos*100:.2f}%)\n")
        f.write(f"  - 总计被拒: {reject_budget + reject_capacity + reject_no_station:,}\n\n")

        if best_res:
            f.write("【最优加权和配置】\n")
            f.write(f"小区建设状态 (0=无, 1=小, 2=中, 3=大): {best_res['config']}\n")
            config_str = ''.join(str(c) for c in best_res['config'])
            f.write(f"配置字符串: {config_str}\n")
            f.write(f"总建设成本: {best_res['cost']} 万元\n")
            f.write(f"覆盖率: {best_res['coverage'] * 100:.2f}%\n")
            f.write(f"平均满意度: {best_res['satisfaction']:.4f}\n")
            f.write(f"加权得分: {best_score:.4f}\n")
            f.write(f"是否收敛: {'是' if best_res.get('converged', False) else '否'}\n")
            f.write("站点覆盖分配详情:\n")
            for st, comms in best_res['allocation'].items():
                comms_str = [COMMUNITIES[x] for x in comms]
                load = best_res.get('actual_loads', {}).get(st, best_res.get('station_loads', {}).get(st, 0))
                cap = best_res['stations'][st]
                util = load / cap * 100 if cap > 0 else 0
                station_type_code = best_res['config'][st]
                type_name = ['无', '小型', '中型', '大型'][station_type_code]
                f.write(f"  - 站点 {COMMUNITIES[st]} ({type_name}, 容量:{cap}, 负载:{load:.0f}, 利用率:{util:.1f}%) 覆盖小区: {', '.join(comms_str)}\n")

            f.write(f"\n【帕累托前沿解数量】: {len(pareto_front)}\n")
            
            f.write("\n【帕累托前沿Top10解】\n")
            f.write(f"{'排名':<6} {'覆盖率':<10} {'满意度':<10} {'得分':<12} {'配置字符串'}\n")
            f.write("-" * 80 + "\n")
            for rank, (cov, sat, cfg, raw_sc) in enumerate(pareto_front_sorted[:10], 1):
                cfg_str = ''.join(str(c) for c in cfg)
                f.write(f"{rank:<6} {cov*100:<9.2f}% {sat:<9.4f} {raw_sc:<11.4f} {cfg_str}\n")
        else:
            f.write("未找到任何满足约束的可行解。\n")
            f.write("\n可能原因：\n")
            f.write("1. 所有配置都超出预算限制（120万元）\n")
            f.write("2. 所有配置都存在服务站容量超载\n")
            f.write("3. 需求数据过大，即使建大型站也无法容纳\n")

    print(f"\n枚举完成，耗时 {run_time:.2f} 秒，结果保存在 {out_dir}")
    print(f"有效解数量: {valid_count}")
    if best_res:
        print(f"最优得分: {best_score:.4f}")
        print(f"最优配置: {''.join(str(c) for c in best_res['config'])}")
        print(f"覆盖率: {best_res['coverage']*100:.2f}%")
        print(f"满意度: {best_res['satisfaction']:.4f}")
    else:
        print("未找到可行解，请查看诊断报告")

    if best_res:
        plot_pareto_front(pareto_front, best_res, out_dir)
        print(f"帕累托前沿图已保存至: {os.path.join(out_dir, 'pareto_front.png')}")
        
        output_profit_and_satisfaction(best_res, out_dir)
        
        plot_map(best_res['allocation'], out_dir)
        print(f"覆盖地图已保存至: {os.path.join(out_dir, 'coverage_map.png')}")
        
        json_path = os.path.join(BASE_DIR, "optimum_config.json")
        with open(json_path, "w") as f:
            json.dump(list(best_res['config']), f)


if __name__ == "__main__":
    main()
