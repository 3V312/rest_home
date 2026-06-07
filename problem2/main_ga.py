import os
import json
import time
import random
import numpy as np
import matplotlib.pyplot as plt
from config2 import *

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

POP_SIZE = 300
GENERATIONS = 500
CROSSOVER_RATE = 0.85
INITIAL_MUTATION_RATE = 0.25
MIN_MUTATION_RATE = 0.05
ELITE_SIZE = 5
TOURNAMENT_SIZE = 3
MUTATION_DECAY_INTERVAL = 80
MUTATION_DECAY_FACTOR = 0.95


def get_latest_enum_score():
    """获取指定枚举最优得分（使用 enum_20260523_152013）"""
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    if not os.path.exists(results_dir):
        return None
    
    # 指定使用特定的枚举结果目录
    target_folder = "enum_20260523_152013"
    result_file = os.path.join(results_dir, target_folder, "enumerate_result.txt")
    
    if not os.path.exists(result_file):
        print(f"警告：未找到指定的枚举结果文件: {result_file}")
        return None
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                if "加权得分:" in line or "原始加权得分:" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        score_str = parts[-1].strip()
                        score_str = ''.join(c for c in score_str if c.isdigit() or c == '.')
                        if score_str:
                            return float(score_str)
    except Exception as e:
        print(f"警告：读取枚举结果失败 - {e}")
    
    return None


ENUM_OPTIMAL_SCORE = get_latest_enum_score() or 0.9669


def fitness(chromosome):
    """计算个体适应度（满意度驱动的动态分配）"""
    total_cost = sum(CONSTRUCTION_COST[s] for s in chromosome)
    if total_cost > BUDGET_MAX:
        return -1.0, 0.0, 0.0

    stations = {i: MAX_CAPACITY[s] for i, s in enumerate(chromosome) if s > 0}
    if not stations:
        return -1.0, 0.0, 0.0

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
            return -1.0, 0.0, 0.0

    max_iterations = 30
    for iteration in range(max_iterations):
        theoretical_demand = {i: 0.0 for i in stations.keys()}
        for st_idx, comms in allocation.items():
            for comm_idx in comms:
                theoretical_demand[st_idx] += DAILY_DEMAND[comm_idx]

        utilization = {}
        for st_idx in stations:
            cap = stations[st_idx]
            demand = theoretical_demand[st_idx]
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
                return -1.0, 0.0, 0.0

            if set(new_allocation[st_idx]) != set(allocation.get(st_idx, [])):
                allocation_changed = True

        allocation = new_allocation
        if not allocation_changed:
            break

    theoretical_demand = {i: 0.0 for i in stations.keys()}
    for st_idx, comms in allocation.items():
        for comm_idx in comms:
            theoretical_demand[st_idx] += DAILY_DEMAND[comm_idx]

    truncation_factors = {}
    utilization = {}
    for st_idx in stations:
        cap = stations[st_idx]
        demand = theoretical_demand[st_idx]
        if demand > cap and demand > 0:
            truncation_factors[st_idx] = cap / demand
        else:
            truncation_factors[st_idx] = 1.0
        utilization[st_idx] = min(demand / cap, 1.0) if cap > 0 else 0.0

    covered_elderly = 0
    total_satisfaction_score = 0.0

    for st_idx, comms in allocation.items():
        tf = truncation_factors[st_idx]
        
        for comm_idx in comms:
            d = DIST_MATRIX[comm_idx][st_idx]
            s3 = calc_community_s3(comm_idx)
            sat = calc_satisfaction_dynamic(d, utilization[st_idx], s3)
            
            actual_served = ELDERLY_POP[comm_idx] * tf
            covered_elderly += actual_served
            total_satisfaction_score += sat * actual_served

    cov = covered_elderly / TOTAL_ELDERLY
    sat = (total_satisfaction_score / covered_elderly) if covered_elderly > 0 else 0.0

    score = 0.5 * cov + 0.5 * sat
    score = max(score, 0.0)

    return score, cov, sat


def init_population():
    random.seed(42)
    np.random.seed(42)
    pop = []
    while len(pop) < POP_SIZE:
        chrom = [random.randint(0, 3) for _ in range(10)]
        cost = sum(CONSTRUCTION_COST[s] for s in chrom)
        if cost <= BUDGET_MAX * 1.2:
            pop.append(chrom)
    return pop


def get_mutation_rate(gen):
    decay_times = gen // MUTATION_DECAY_INTERVAL
    rate = INITIAL_MUTATION_RATE * (MUTATION_DECAY_FACTOR ** decay_times)
    return max(rate, MIN_MUTATION_RATE)


def tournament_selection(pop, fitnesses, k=TOURNAMENT_SIZE):
    selected = []
    for _ in range(POP_SIZE - ELITE_SIZE):
        participants = random.sample(list(zip(pop, fitnesses)), k)
        winner = max(participants, key=lambda x: x[1][0])
        selected.append(winner[0])
    return selected


def crossover(parent1, parent2):
    if random.random() < CROSSOVER_RATE:
        pt = random.randint(1, 8)
        child1 = parent1[:pt] + parent2[pt:]
        child2 = parent2[:pt] + parent1[pt:]
        return child1, child2
    return parent1[:], parent2[:]


def mutate(child, mutation_rate):
    for idx in range(len(child)):
        if random.random() < mutation_rate:
            child[idx] = random.randint(0, 3)
    return child


def compare_with_enum(ga_best_config, ga_metrics, ga_time):
    """GA结果与指定枚举结果对比（使用 enum_20260523_152013）"""
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    target_folder = "enum_20260523_152013"
    enum_result_file = os.path.join(results_dir, target_folder, "enumerate_result.txt")
    
    print("\n" + "=" * 70)
    print("GA vs 枚举法对比分析")
    print("=" * 70)
    print(f"使用的枚举结果目录: {target_folder}")
    print(f"使用的枚举最优得分参考值: {ENUM_OPTIMAL_SCORE:.4f}")
    
    if not os.path.exists(enum_result_file):
        print(f"\n警告: 未找到枚举结果文件: {enum_result_file}")
        if ga_metrics:
            ga_cov, ga_sat = ga_metrics[0], ga_metrics[1]
            ga_score = 0.5 * ga_cov + 0.5 * ga_sat
            print(f"\nGA最优指标:")
            print(f"  覆盖率: {ga_cov * 100:.4f}%")
            print(f"  满意度: {ga_sat:.4f}")
            print(f"  加权得分: {ga_score:.4f}")
            print(f"\n与枚举最优得分差距: {abs(ENUM_OPTIMAL_SCORE - ga_score):.4f}")
        return

    enum_config = None
    enum_score = ENUM_OPTIMAL_SCORE
    
    try:
        with open(enum_result_file, 'r', encoding='utf-8') as f:
            for line in f:
                if "小区建设状态" in line:
                    # 解析配置：小区建设状态 (0=无, 1=小, 2=中, 3=大): (0, 0, 1, 0, 2, 0, 0, 1, 0, 3)
                    parts = line.split(":")
                    if len(parts) >= 2:
                        config_str = parts[-1].strip().strip("()")
                        enum_config = [int(x.strip()) for x in config_str.split(",")]
                elif "加权得分:" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        enum_score = float(parts[-1].strip())
    except Exception as e:
        print(f"解析枚举结果失败: {e}")
        return
    
    if enum_config is None:
        print("\n警告: 无法从枚举结果中解析配置")
        return

    hamming_dist = sum(1 for a, b in zip(ga_best_config, enum_config) if a != b)
    enum_result = evaluate_configuration_for_comparison(tuple(enum_config))

    if enum_result:
        enum_cov, enum_sat = enum_result['coverage'], enum_result['satisfaction']
        ga_cov, ga_sat = ga_metrics[0], ga_metrics[1]
        
        ga_score = 0.5 * ga_cov + 0.5 * ga_sat

        print(f"配置差异 (汉明距离): {hamming_dist}")
        print(f"枚举最优配置: {enum_config}")
        print(f"GA最优配置:   {ga_best_config}")
        print(f"\n覆盖率对比:")
        print(f"  枚举: {enum_cov * 100:.4f}%")
        print(f"  GA:   {ga_cov * 100:.4f}%")
        print(f"  差值: {(ga_cov - enum_cov) * 100:+.4f}%")
        print(f"\n满意度对比:")
        print(f"  枚举: {enum_sat:.4f}")
        print(f"  GA:   {ga_sat:.4f}")
        print(f"  差值: {ga_sat - enum_sat:+.4f}")
        print(f"\n加权得分对比:")
        print(f"  枚举: {enum_score:.4f}")
        print(f"  GA:   {ga_score:.4f}")
        print(f"  差值: {ga_score - enum_score:+.4f}")

        if hamming_dist == 0:
            print("\nGA找到了与枚举完全相同的解！")
        elif abs(ga_cov - enum_cov) < 0.0001 and abs(ga_sat - enum_sat) < 0.0001:
            print("\nGA找到了与枚举等效的解。")
        else:
            gap = abs(enum_score - ga_score)
            print(f"\nGA解与枚举解存在差异（差距: {gap:.4f}）。")

    print(f"\n运行时间对比:")
    print(f"  枚举法: ~1.87 秒")
    print(f"  GA:     {ga_time:.2f} 秒")
    print(f"\n复杂度分析:")
    print(f"  - 枚举法: O(4^n)，当 n=20 时需 4^20 ≈ 10^12 次运算")
    print(f"  - GA:     O(G * P * n^2)，当 n=20,30 时仍可高效求解")
    print(f"  - 结论: 小区数量增加时，GA优势显著")


def evaluate_configuration_for_comparison(config_tuple):
    """评估配置用于结果对比"""
    total_cost = sum(CONSTRUCTION_COST[s] for s in config_tuple)
    if total_cost > BUDGET_MAX:
        return None

    stations = {i: MAX_CAPACITY[s] for i, s in enumerate(config_tuple) if s > 0}
    if not stations:
        return None

    allocation = {i: [] for i in stations.keys()}
    station_loads = {i: 0.0 for i in stations.keys()}

    for j in range(10):
        best_station = -1
        best_dist = float('inf')
        for i in stations.keys():
            d = DIST_MATRIX[j][i]
            if d <= SERVICE_RADIUS and d < best_dist:
                best_dist = d
                best_station = i
        if best_station != -1:
            allocation[best_station].append(j)
            station_loads[best_station] += DAILY_DEMAND[j]

    for st_idx, comms in allocation.items():
        if not comms:
            return None

    for i in stations.keys():
        if station_loads[i] > stations[i]:
            station_loads[i] = float(stations[i])

    covered_elderly = 0
    total_satisfaction_score = 0.0

    for st_idx, comms in sorted(allocation.items()):
        utilization = station_loads[st_idx] / stations[st_idx]
        utilization = min(utilization, 1.0)
        for comm_idx in comms:
            d = DIST_MATRIX[comm_idx][st_idx]
            s3 = calc_community_s3(comm_idx)
            sat = calc_satisfaction_dynamic(d, utilization, s3)
            covered_elderly += ELDERLY_POP[comm_idx]
            total_satisfaction_score += sat * ELDERLY_POP[comm_idx]

    coverage_rate = covered_elderly / TOTAL_ELDERLY
    avg_satisfaction = (total_satisfaction_score / covered_elderly) if covered_elderly > 0 else 0.0

    return {
        'config': config_tuple,
        'allocation': allocation,
        'station_loads': station_loads,
        'stations': stations,
        'coverage': coverage_rate,
        'satisfaction': avg_satisfaction
    }


def output_ga_full_result(ga_best_config, ga_metrics, out_dir):
    """输出GA详细结果报告"""
    result = evaluate_configuration_for_comparison(tuple(ga_best_config))
    if not result:
        print("警告：无法为最终的最佳配置生成报告。")
        return

    txt_path = os.path.join(out_dir, "ga_full_result.txt")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 70 + "\n")
        f.write("遗传算法(GA)求解结果详细分析\n")
        f.write("=" * 70 + "\n\n")

        f.write("【一、最优配置】\n")
        f.write(f"小区建设状态 (0=无, 1=小, 2=中, 3=大): {ga_best_config}\n")
        f.write(f"覆盖率: {ga_metrics[0] * 100:.4f}%\n")
        f.write(f"平均满意度: {ga_metrics[1]:.4f}\n")
        f.write(f"加权得分: {0.5 * ga_metrics[0] + 0.5 * ga_metrics[1]:.4f}\n\n")

        f.write("【二、服务站覆盖分配】\n")
        for st_idx, comms in sorted(result['allocation'].items()):
            comms_str = [COMMUNITIES[c] for c in comms]
            station_type = ga_best_config[st_idx]
            type_name = ['无', '小型', '中型', '大型'][station_type]
            f.write(f"  - 站点 {COMMUNITIES[st_idx]} ({type_name}) 覆盖小区: {', '.join(comms_str)}\n")

        f.write("\n【三、分小区满意度】\n")
        f.write(f"{'小区':<8} {'分配站点':<10} {'距离(m)':<10} {'距离满意度':<12} {'响应满意度':<12} {'价格满意度':<12} {'综合满意度':<12}\n")
        f.write("-" * 70 + "\n")

        for st_idx, comms in sorted(result['allocation'].items()):
            utilization = result['station_loads'][st_idx] / result['stations'][st_idx]
            utilization = min(utilization, 1.0)
            for comm_idx in comms:
                d = DIST_MATRIX[comm_idx][st_idx]
                s1 = calc_s1(d)
                s2 = calc_s2(utilization)
                s3 = calc_community_s3(comm_idx)
                sat = W1 * s1 + W2 * s2 + W3 * s3
                f.write(f"{COMMUNITIES[comm_idx]:<8} {COMMUNITIES[st_idx]:<10} {d:<10} {s1:<11.4f} {s2:<11.4f} {s3:<11.4f} {sat:<11.4f}\n")

        f.write("\n【四、服务站年度利润分析】\n")
        f.write("-" * 70 + "\n")
        f.write(f"{'站点':<8} {'类型':<6} {'年收入(元)':<15} {'年支出(元)':<15} {'年利润(元)':<15}\n")
        f.write("-" * 70 + "\n")

        total_revenue = 0
        total_expense = 0
        total_profit = 0

        for st_idx in sorted(result['allocation'].keys()):
            station_type = ga_best_config[st_idx]
            type_name = ['无', '小型', '中型', '大型'][station_type]

            revenue, expense, profit = calc_station_profit(
                st_idx, result['allocation'][st_idx], result['allocation'],
                result['station_loads'], result['stations']
            )

            total_revenue += revenue
            total_expense += expense
            total_profit += profit

            f.write(f"{COMMUNITIES[st_idx]:<8} {type_name:<6} {revenue:<15,.0f} {expense:<15,.0f} {profit:<15,.0f}\n")

        f.write("-" * 70 + "\n")
        f.write(f"{'总计':<8} {'':<6} {total_revenue:<15,.0f} {total_expense:<15,.0f} {total_profit:<15,.0f}\n\n")

        f.write("【五、全局指标】\n")
        f.write(f"服务覆盖率: {result['coverage'] * 100:.2f}%\n")
        f.write(f"平均满意度: {result['satisfaction']:.4f}\n")
        f.write(f"加权得分: {0.5 * result['coverage'] + 0.5 * result['satisfaction']:.4f}\n")

    print(f"GA详细结果已保存至: {txt_path}")


def main():
    """遗传算法主函数"""
    start_time = time.time()
    pop = init_population()

    best_history = []
    avg_history = []
    global_best_score = -1.0
    global_best_chrom = None
    global_best_metrics = None

    first_gen_best = None
    last_gen_best = None
    converge_gen = None
    early_stop_gen = None

    prev_best_score = -1.0
    no_improve_count = 0

    print(f"开始遗传算法，种群大小: {POP_SIZE}, 代数: {GENERATIONS}")
    print(f"动态变异率: 初始={INITIAL_MUTATION_RATE}, 最低={MIN_MUTATION_RATE}, 衰减间隔={MUTATION_DECAY_INTERVAL}代")

    for gen in range(GENERATIONS):
        mutation_rate = get_mutation_rate(gen)

        fits = [fitness(ind) for ind in pop]

        scores = [f[0] for f in fits if f[0] > 0]
        if scores:
            avg_score = sum(scores) / len(scores)
            current_best = max(scores)
        else:
            avg_score = 0
            current_best = 0

        for i, (score, cov, sat) in enumerate(fits):
            if score > global_best_score:
                global_best_score = score
                global_best_chrom = pop[i][:]
                global_best_metrics = (cov, sat)

        if gen == 0:
            first_gen_best = global_best_score
        last_gen_best = global_best_score

        if converge_gen is None and abs(global_best_score - ENUM_OPTIMAL_SCORE) < 0.001:
            converge_gen = gen + 1

        if abs(global_best_score - prev_best_score) < 1e-6:
            no_improve_count += 1
        else:
            no_improve_count = 0

        prev_best_score = global_best_score

        best_history.append(global_best_score)
        avg_history.append(avg_score)

        if (gen + 1) % 20 == 0 or gen == 0:
            elapsed = time.time() - start_time
            print(f"第 {gen + 1}/{GENERATIONS} 代, 最优得分: {global_best_score:.4f}, "
                  f"覆盖率: {global_best_metrics[0]:.4f}, 满意度: {global_best_metrics[1]:.4f}, "
                  f"变异率: {mutation_rate:.3f}, 耗时: {elapsed:.1f}s")

        elite_indices = sorted(range(len(fits)), key=lambda i: fits[i][0], reverse=True)[:ELITE_SIZE]
        elite_pop = [pop[i][:] for i in elite_indices]

        selected = tournament_selection(pop, fits)

        next_pop = elite_pop[:]

        for i in range(0, len(selected), 2):
            p1 = selected[i]
            p2 = selected[i + 1] if i + 1 < len(selected) else selected[0]
            c1, c2 = crossover(p1, p2)
            c1 = mutate(c1, mutation_rate)
            c2 = mutate(c2, mutation_rate)
            next_pop.extend([c1, c2])

        pop = next_pop[:POP_SIZE]

    run_time = time.time() - start_time
    out_dir = get_out_dir("ga")

    print(f"\nGA 完成，总耗时: {run_time:.2f} 秒")
    
    if global_best_chrom is None or global_best_metrics is None:
        print("GA 未找到任何可行解！")
        print("可能原因：")
        print("  1. 预算约束过严")
        print("  2. 需求数据过大")
        print("  3. 初始化种群质量差")
        print("\n建议：")
        print("  - 检查 config2.py 中的配置")
        print("  - 尝试增加种群大小或代数")
        print("  - 放宽预算或容量约束")
        return
    
    print(f"最优配置: {global_best_chrom}")
    print(
        f"最优加权得分: {global_best_score:.4f} (覆盖率: {global_best_metrics[0]:.4f}, 满意度: {global_best_metrics[1]:.4f})")

    print(f"\n收敛统计分析:")
    print(f"  第一代最佳适应度: {first_gen_best:.4f}")
    print(f"  最后一代最佳适应度: {last_gen_best:.4f}")
    if converge_gen:
        print(f"  达到枚举最优值({ENUM_OPTIMAL_SCORE})的代数: 第 {converge_gen} 代")
    else:
        print(f"  在{GENERATIONS}代内未达到枚举最优值({ENUM_OPTIMAL_SCORE})")
    if early_stop_gen:
        print(f"  提前终止代数: 第 {early_stop_gen} 代")

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(range(len(best_history)), best_history, label='最佳适应度', linewidth=2, color='red')
    ax.plot(range(len(avg_history)), avg_history, label='平均适应度', linewidth=2, color='blue', linestyle='--')
    ax.axhline(y=ENUM_OPTIMAL_SCORE, color='green', linestyle=':', linewidth=1.5,
               label=f'枚举最优值 ({ENUM_OPTIMAL_SCORE})')
    ax.set_xlabel('代数', fontsize=12)
    ax.set_ylabel('适应度', fontsize=12)
    ax.set_title('遗传算法收敛曲线', fontsize=14)
    ax.legend(frameon=False, loc='lower right')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "ga_convergence.png"), dpi=300, facecolor='w', bbox_inches='tight')
    plt.close()

    compare_with_enum(global_best_chrom, global_best_metrics, run_time)
    output_ga_full_result(global_best_chrom, global_best_metrics, out_dir)


if __name__ == "__main__":
    main()