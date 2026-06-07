import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import config3 as cfg
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime

matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

# 输出目录
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
OUT_DIR = os.path.join(os.path.dirname(__file__), 'results', f'3_{timestamp}')
os.makedirs(OUT_DIR, exist_ok=True)

#给出运营指标
def get_station_metrics(prices, station_info, use_subsidy=True):

    max_iter = 15
    converged = False
    current_utilization = 0.5
    s2_current = cfg.satisfaction_S2(current_utilization)
    
    for iteration in range(max_iter):
        total_daily_services = np.zeros(6)
        
        for item in station_info['covered']:
            comm = item['community']
            distance = item['distance']
            s1 = cfg.satisfaction_S1(distance)
            elderly_struct = cfg.ELDERLY_BY_TYPE_Y5[comm]
            demand_by_type = cfg.DEMAND_BY_TYPE_MONTHLY[comm]
            s3_vector = np.array([cfg.satisfaction_S3(prices[j], cfg.BASE_PRICE[j]) for j in range(6)])
            avg_s3 = np.mean(s3_vector)
            overall_satisfaction = 0.2 * s1 + 0.3 * s2_current + 0.5 * avg_s3
            for elderly_type in ['自理', '半失能', '失能']:
                count = elderly_struct[elderly_type]
                if count == 0:
                    continue
                monthly_demand = np.array(demand_by_type[elderly_type], dtype=float)
                daily_demand = (monthly_demand / 30) * overall_satisfaction
                total_daily_services += daily_demand
        
        capacity = station_info['capacity_per_day']
        total_demand_sum = np.sum(total_daily_services)
        
        if total_demand_sum > capacity:
            scale_factor = capacity / total_demand_sum
            actual_daily_services = total_daily_services * scale_factor
        else:
            actual_daily_services = total_daily_services
        new_utilization = np.sum(actual_daily_services) / capacity if capacity > 0 else 0
        if abs(new_utilization - current_utilization) < 0.005:
            converged = True
            current_utilization = new_utilization
            break
        current_utilization = new_utilization
        s2_current = cfg.satisfaction_S2(current_utilization)
    
    utilization = current_utilization
    s2 = cfg.satisfaction_S2(utilization)
    details = {}
    for item in station_info['covered']:
        comm = item['community']
        distance = item['distance']
        s1 = cfg.satisfaction_S1(distance)
        
        elderly_struct = cfg.ELDERLY_BY_TYPE_Y5[comm]
        
        s3_vector = np.array([cfg.satisfaction_S3(prices[j], cfg.BASE_PRICE[j]) for j in range(6)])
        avg_s3 = np.mean(s3_vector)
        
        corrected_overall_satisfaction = 0.2 * s1 + 0.3 * s2 + 0.5 * avg_s3
        
        details[comm] = {
            'avg_s': corrected_overall_satisfaction,
            'avg_s3': avg_s3,
            'utilization': utilization,
            's_vector': s3_vector,
            'elderly_count': sum(elderly_struct.values()),
            'total_demand': 0.0,
            'total_weighted_satisfaction': 0.0
        }
    
    daily_revenue = np.dot(actual_daily_services, prices)
    annual_revenue = daily_revenue * 365
    annual_subsidy = 0.0
    if use_subsidy:
        subsidy_per_day = np.sum(actual_daily_services[:5]) * cfg.SUBSIDY_PER_SERVICE
        station_type = station_info['type']
        type_map = {'小型': 1, '中型': 2, '大型': 3}
        type_key = type_map[station_type]
        daily_cap = cfg.DAILY_SUBSIDY_CAP[type_key]
        
        if subsidy_per_day > daily_cap:
            subsidy_per_day = daily_cap
            
        annual_subsidy = subsidy_per_day * 365
    daily_variable_cost = np.dot(actual_daily_services, cfg.BASE_PRICE)
    annual_variable_cost = daily_variable_cost * 365
    
    annual_total_cost = station_info['annual_operating_cost'] + annual_variable_cost
    
    profit = annual_revenue + annual_subsidy - annual_total_cost
    margin = (annual_revenue + annual_subsidy - annual_total_cost) / annual_total_cost if annual_total_cost > 0 else -1.0
    meets_margin_constraint = 0 <= margin <= cfg.PROFIT_MARGIN_MAX
    return {
        'utilization': utilization * 100,
        'annual_revenue': annual_revenue,
        'annual_subsidy': annual_subsidy,
        'profit': profit,
        'margin': margin,
        'meets_margin_constraint': meets_margin_constraint,
        's2_score': s2,
        'details': details,
        'converged': converged,
        'iterations': iteration + 1,
        'actual_daily_services': actual_daily_services,
        'total_demand_before_truncation': total_demand_sum
    }

#寻找最优定价策略
def optimize_station_prices(station_info, use_subsidy=True):

    from scipy.optimize import NonlinearConstraint
    def objective(prices_5):
        full_prices = np.append(prices_5, 0.0)
        metrics = get_station_metrics(full_prices, station_info, use_subsidy)

        satisfaction_data = metrics['details']
        total_weighted_satisfaction = 0.0
        total_elderly = 0
        
        for comm_data in satisfaction_data.values():
            weight = comm_data['elderly_count']
            avg_s = comm_data['avg_s']
            total_weighted_satisfaction += avg_s * weight
            total_elderly += weight
        
        avg_overall_satisfaction = total_weighted_satisfaction / total_elderly if total_elderly > 0 else 0

        return -avg_overall_satisfaction

    x0 = np.array(cfg.BASE_PRICE[:5])
    bounds = [(cfg.BASE_PRICE[i] * 0.7, cfg.BASE_PRICE[i] * 1.5) for i in range(5)]
    def margin_constraint_func(prices_5):
        """利润率约束：必须满足 0 <= 利润率 <= 8%"""
        full_prices = np.append(prices_5, 0.0)
        metrics = get_station_metrics(full_prices, station_info, use_subsidy)
        return metrics['margin']

    margin_constraint = NonlinearConstraint(
        margin_constraint_func, 
        lb=0.0, 
        ub=cfg.PROFIT_MARGIN_MAX
    )

    def subsidy_cap_constraint(prices_5):
        """补贴上限约束：日补贴不能超过服务站类型对应的上限"""
        full_prices = np.append(prices_5, 0.0)
        metrics = get_station_metrics(full_prices, station_info, use_subsidy)
        daily_subsidy = metrics['annual_subsidy'] / 365
        
        station_type = station_info['type']
        type_map = {'小型': 1, '中型': 2, '大型': 3}
        type_key = type_map[station_type]
        daily_cap = cfg.DAILY_SUBSIDY_CAP[type_key]

        return daily_cap - daily_subsidy
    
    subsidy_constraint = NonlinearConstraint(
        subsidy_cap_constraint,
        lb=0.0,
        ub=float('inf')
    )
    
    # 使用 trust-constr 算法（适合处理非线性约束）
    result = minimize(
        objective, x0, method='trust-constr', bounds=bounds, 
        constraints=[margin_constraint, subsidy_constraint],
        options={'maxiter': 1000, 'gtol': 1e-8, 'xtol': 1e-8, 'verbose': 0}  # 关闭详细输出
    )
    
    final_prices = np.append(result.x, 0.0)
    final_metrics = get_station_metrics(final_prices, station_info, use_subsidy)
    
    # 输出详细检查结果
    util = final_metrics['utilization']
    cap = station_info['capacity_per_day']
    demand_before = final_metrics['total_demand_before_truncation']
    demand_after = np.sum(final_metrics['actual_daily_services'])
    margin = final_metrics['margin'] * 100
    
    print(f"  ✓ 优化完成（方法：trust-constr）")
    print(f"  结果检查：")
    print(f"     迭代次数: {final_metrics['iterations']}, 收敛: {final_metrics['converged']}")
    print(f"     截断前总需求: {demand_before:.1f}, 截断后实际服务: {demand_after:.1f}")
    print(f"     需求={demand_after:.0f}, 容量={cap}, 利用率={util:.1f}%")
    print(f"     年收入={final_metrics['annual_revenue']:.0f}, "
          f"年补贴={final_metrics['annual_subsidy']:.0f}, "
          f"年成本={station_info['annual_operating_cost']:.0f}")
    print(f"     利润率={margin:.2f}%")

    
    return final_prices

#画图
def generate_visualizations(results_dict, out_dir):
    """
    生成4张分析图表并保存到结果文件夹
    
    参数:
    results_dict: 包含完整求解结果的字典
    out_dir: 输出目录路径
    """
    print("\n正在生成可视化图表...")
    
    # ==================== 图1：各服务站服务定价对比（分组柱状图） ====================
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    
    services_to_plot = cfg.SERVICES[:5]  # 排除紧急救助
    service_names_cn = ['助餐', '日间照料', '上门护理', '康复理疗', '助浴']
    station_names = [st['name'] for st in results_dict['stations_info']]
    station_types = [st['type'] for st in results_dict['stations_info']]
    
    x = np.arange(len(station_names))
    width = 0.15
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#6A994E']
    
    for i, (svc_name_cn, svc_idx) in enumerate(zip(service_names_cn, range(5))):
        prices = [results_dict['optimal_prices_sub'][j][svc_idx] for j in range(len(station_names))]
        bars = ax1.bar(x + i * width, prices, width, label=svc_name_cn, color=colors[i], alpha=0.85)
        
        # 添加数值标签
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    ax1.set_xlabel('服务站编号', fontsize=12, fontweight='bold')
    ax1.set_ylabel('定价（元/次）', fontsize=12, fontweight='bold')
    ax1.set_title('图1 不同规模服务站各项服务最优定价对比', fontsize=14, fontweight='bold', pad=15)
    ax1.set_xticks(x + width * 2)
    ax1.set_xticklabels([f'{name}\n({stype})' for name, stype in zip(station_names, station_types)], fontsize=10)
    ax1.legend(loc='upper left', fontsize=9, framealpha=0.9)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_ylim(0, max([max(results_dict['optimal_prices_sub'][j][:5]) for j in range(len(station_names))]) * 1.2)
    
    plt.tight_layout()
    fig1_path = os.path.join(out_dir, "fig1_pricing_comparison.png")
    plt.savefig(fig1_path, dpi=300, bbox_inches='tight', format='png')
    plt.close()
    print(f"✓ 图1已保存: {fig1_path}")
    
    # ==================== 图2：各服务站年总利润与利润率（双轴图） ====================
    fig2, ax2 = plt.subplots(figsize=(12, 7))
    
    station_labels = [st['name'] for st in results_dict['stations_info']]
    profits = [metrics['profit'] for metrics in results_dict['metrics_sub']]
    margins_pct = [metrics['margin'] * 100 for metrics in results_dict['metrics_sub']]
    
    x2 = np.arange(len(station_labels))
    width2 = 0.6
    colors_profit = ['#2E86AB', '#A23B72', '#F18F01']
    
    # 左轴：年总利润（柱状图）
    bars_profit = ax2.bar(x2, profits, width2, color=[colors_profit[i % len(colors_profit)] for i in range(len(station_labels))], 
                          alpha=0.85, label='年总利润', edgecolor='white', linewidth=0.5)
    
    # 添加利润数值标签
    for bar in bars_profit:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height/10000:.1f}万', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax2.set_xlabel('服务站编号', fontsize=12, fontweight='bold')
    ax2.set_ylabel('年总利润（元）', fontsize=12, fontweight='bold', color='#2E86AB')
    ax2.tick_params(axis='y', labelcolor='#2E86AB')
    ax2.set_title('图2 各服务站年总利润与利润率（8%约束满足情况）', fontsize=14, fontweight='bold', pad=15)
    ax2.set_xticks(x2)
    ax2.set_xticklabels(station_labels, fontsize=11)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 右轴：利润率（折线图）- 关键修复：动态设置Y轴范围
    ax3 = ax2.twinx()
    line_margin = ax3.plot(x2, margins_pct, 'ro-', linewidth=2.5, markersize=10, 
                           markeredgecolor='darkred', markeredgewidth=2, label='利润率', zorder=5)
    
    # 添加利润率数值标签
    margin_max = max(margins_pct) if margins_pct else 0
    for i, margin in enumerate(margins_pct):
        ax3.text(i, margin + margin_max * 0.02, f'{margin:.2f}%', ha='center', va='bottom', 
                fontsize=9, fontweight='bold', color='darkred')
    
    ax3.set_ylabel('利润率（%）', fontsize=12, fontweight='bold', color='darkred')
    ax3.tick_params(axis='y', labelcolor='darkred')
    
    # 动态设置利润率Y轴范围（避免固定0-10导致数据被压缩）
    margin_min = min(margins_pct) if margins_pct else 0
    margin_max = max(margins_pct) if margins_pct else 0
    margin_range = margin_max - margin_min
    
    # 关键修复：防止极端值和除零错误
    if margin_range < 0.01:  # 如果范围太小，使用默认扩展
        margin_range = 1.0
        margin_min = margin_min - 0.5
        margin_max = margin_max + 0.5
    
    ax3.set_ylim(margin_min - margin_range * 0.1, margin_max + margin_range * 0.3)
    
    # 添加8%参考线
    ax3.axhline(y=cfg.PROFIT_MARGIN_MAX * 100, color='red', linestyle='--', linewidth=2, 
               label=f'利润率上限 {cfg.PROFIT_MARGIN_MAX*100:.0f}%', alpha=0.7)
    
    # 合并图例
    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax3.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10, framealpha=0.9)
    
    plt.tight_layout()
    fig2_path = os.path.join(out_dir, "fig2_profit_margin.png")
    # 关键修复：移除pad_inches参数，避免边界框计算异常
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ 图2已保存: {fig2_path}")
    
    # ==================== 图3：各小区综合满意度与价格满意度对比（分组柱状图） ====================
    fig3, ax4 = plt.subplots(figsize=(14, 7))
    
    communities = cfg.COMMUNITIES
    satisfaction_scores = []
    price_scores = []
    
    for comm in communities:
        # 查找该小区所属服务站
        assigned_station = None
        for st_info in results_dict['stations_info']:
            if comm in [item['community'] for item in st_info['covered']]:
                assigned_station = st_info['name']
                break
        
        if assigned_station and assigned_station in results_dict['satisfaction_data']:
            comm_data = results_dict['satisfaction_data'][assigned_station]['details'].get(comm, {})
            avg_s = comm_data.get('avg_s', 0.0)
            avg_s3 = comm_data.get('avg_s3', 0.0)
        else:
            avg_s = 0.0
            avg_s3 = 0.0
        
        satisfaction_scores.append(avg_s)
        price_scores.append(avg_s3)
    
    x3 = np.arange(len(communities))
    width3 = 0.35
    
    bars_sat = ax4.bar(x3 - width3/2, satisfaction_scores, width3, label='综合满意度', 
                       color='#2E86AB', alpha=0.85, edgecolor='white')
    bars_price = ax4.bar(x3 + width3/2, price_scores, width3, label='价格满意度', 
                         color='#F18F01', alpha=0.85, edgecolor='white')
    
    # 添加数值标签
    for bar in bars_sat:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    for bar in bars_price:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.3f}', ha='center', va='bottom', fontsize=8)
    
    ax4.set_xlabel('小区编号', fontsize=12, fontweight='bold')
    ax4.set_ylabel('满意度得分', fontsize=12, fontweight='bold')
    ax4.set_title('图3 各小区老人综合满意度与价格满意度', fontsize=14, fontweight='bold', pad=15)
    ax4.set_xticks(x3)
    ax4.set_xticklabels(communities, fontsize=11)
    ax4.legend(loc='lower right', fontsize=11, framealpha=0.9)
    ax4.grid(axis='y', alpha=0.3, linestyle='--')
    ax4.set_ylim(0, max(max(satisfaction_scores), max(price_scores)) * 1.15 if satisfaction_scores else 1.0)
    
    # 添加0.9参考线
    ax4.axhline(y=0.9, color='red', linestyle='--', linewidth=1.5, alpha=0.6, label='参考线 0.9')
    
    plt.tight_layout()
    fig3_path = os.path.join(out_dir, "fig3_satisfaction_comparison.png")
    plt.savefig(fig3_path, dpi=300, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    print(f"✓ 图3已保存: {fig3_path}")
    
    # ==================== 图4：三类老人经济可及性 + 设施利用率 ====================
    fig4, ax5 = plt.subplots(figsize=(12, 7))
    
    # 从 economic_metrics 中提取三类老人的实际支出占比（有/无补贴）
    economic_data = results_dict['economic_metrics']
    groups = ['自理', '半失能', '失能']
    x = np.arange(len(groups))
    width = 0.35
    
    # 有补贴场景的支出占比（已乘以100，单位%）
    actual_A = [economic_data['scenario_A']['actual'][g] * 100 for g in groups]
    actual_B = [economic_data['scenario_B']['actual'][g] * 100 for g in groups]
    
    # 左轴柱状图
    bars_A = ax5.bar(x - width/2, actual_A, width, label='有补贴', color='#A23B72', alpha=0.85, edgecolor='white')
    bars_B = ax5.bar(x + width/2, actual_B, width, label='无补贴', color='#F18F01', alpha=0.85, edgecolor='white')
    
    # 添加数值标签
    for bars in [bars_A, bars_B]:
        for bar in bars:
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height + max(max(actual_A), max(actual_B)) * 0.01,
                    f'{height:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    ax5.set_xlabel('老人类型', fontsize=13, fontweight='bold')
    ax5.set_ylabel('实际支出占比（%）', fontsize=13, fontweight='bold', color='#A23B72')
    ax5.tick_params(axis='y', labelcolor='#A23B72')
    ax5.set_xticks(x)
    ax5.set_xticklabels(groups, fontsize=12)
    ax5.set_ylim(0, max(max(actual_A), max(actual_B)) * 1.2)  # 从0开始
    ax5.grid(axis='y', alpha=0.3, linestyle='--')
    
    # 右轴：设施利用率（两个场景）
    ax6 = ax5.twinx()
    util_A = results_dict['info_metrics']['scenario_A']['avg_utilization']   # 已经是百分比
    util_B = results_dict['info_metrics']['scenario_B']['avg_utilization']
    
    # 将折线点放在两组柱子的中间位置
    pos_A = 0  # 有补贴点在x=0（自理组上方）
    pos_B = 2  # 无补贴点在x=2（失能组上方）
    util_values = [util_A, util_B]
    
    line = ax6.plot([pos_A, pos_B], util_values, 'bo-', linewidth=3, markersize=12,
                    markeredgecolor='darkblue', markeredgewidth=2, label='设施利用率', zorder=5)
    
    # 添加利用率数值标签
    util_max = max(util_values) if util_values else 100
    ax6.text(pos_A, util_A + util_max * 0.02, f'{util_A:.1f}%', ha='center', va='bottom', 
            fontsize=10, fontweight='bold', color='darkblue')
    ax6.text(pos_B, util_B + util_max * 0.02, f'{util_B:.1f}%', ha='center', va='bottom', 
            fontsize=10, fontweight='bold', color='darkblue')
    
    ax6.set_ylabel('设施利用率（%）', fontsize=13, fontweight='bold', color='darkblue')
    ax6.tick_params(axis='y', labelcolor='darkblue')
    ax6.set_ylim(0, util_max * 1.2)  # 从0开始
    
    # 合并图例，置于右下角
    lines1, labels1 = ax5.get_legend_handles_labels()
    lines2, labels2 = ax6.get_legend_handles_labels()
    ax5.legend(lines1 + lines2, labels1 + labels2, loc='lower right', fontsize=11, framealpha=0.9)
    
    plt.title('图4 补贴对不同类型老人经济负担及设施利用率的影响', fontsize=14, fontweight='bold', pad=15)
    plt.tight_layout()
    fig4_path = os.path.join(out_dir, "fig4_accessibility_impact.png")
    plt.savefig(fig4_path, dpi=300, bbox_inches='tight', pad_inches=0.3)
    plt.close()
    print(f"✓ 图4已保存: {fig4_path}")
    
    print("✓ 所有图表生成完成！\n")

#分析可行性
def calculate_quantitative_accessibility(results_dict):
    economic_metrics = {
        'scenario_A': {'actual': {}, 'theory': {}},
        'scenario_B': {'actual': {}, 'theory': {}}
    }
    
    for scenario, prices_dict, sat_data, key in [
        ('A', results_dict['optimal_prices_sub'], results_dict['satisfaction_data'], 'scenario_A'),
        ('B', results_dict['optimal_prices_nosub'], results_dict['satisfaction_data'], 'scenario_B')
    ]:
        comm_data_map = {}
        for st_info, prices in zip(results_dict['stations_info'], prices_dict):
            st_name = st_info['name']
            sat_info = sat_data.get(st_name, {}).get('details', {})
            for item in st_info['covered']:
                comm = item['community']
                comm_data_map[comm] = {
                    'prices': prices,
                    's_vector': sat_info.get(comm, {}).get('s_vector', np.ones(6))
                }

        for group in ['自理', '半失能', '失能']:
            total_actual_expenditure = 0.0
            total_theory_expenditure = 0.0
            total_income = 0.0
            
            for comm in cfg.COMMUNITIES:
                if comm in comm_data_map:
                    prices = comm_data_map[comm]['prices']
                    s_vector = comm_data_map[comm]['s_vector']
                else:
                    prices = np.array(cfg.BASE_PRICE).copy()
                    prices[5] = 0.0
                    s_vector = np.ones(6)
                
                elderly_struct = cfg.ELDERLY_BY_TYPE_Y5[comm]
                comm_income = cfg.INCOME_PER_MONTH[comm]
                demand_by_type = cfg.DEMAND_BY_TYPE_MONTHLY[comm]
                count = elderly_struct[group]
                
                if count == 0:
                    continue
                
                monthly_demand = np.array(demand_by_type[group], dtype=float)
                monthly_actual = np.sum(monthly_demand * s_vector * prices)
                monthly_theory = np.sum(monthly_demand * 1.0 * prices)
                total_actual_expenditure += monthly_actual
                total_theory_expenditure += monthly_theory
                total_income += comm_income * count
            
            if total_income > 0:
                economic_metrics[key]['actual'][group] = total_actual_expenditure / total_income
                economic_metrics[key]['theory'][group] = total_theory_expenditure / total_income
            else:
                economic_metrics[key]['actual'][group] = 0.0
                economic_metrics[key]['theory'][group] = 0.0
    
    geographic_metrics = {}
    
    distance_by_type = {
        '自理': {'weighted_dist': 0.0, 'count': 0, 'covered': 0, 'blind': 0},
        '半失能': {'weighted_dist': 0.0, 'count': 0, 'covered': 0, 'blind': 0},
        '失能': {'weighted_dist': 0.0, 'count': 0, 'covered': 0, 'blind': 0}
    }
    
    for comm_idx, comm in enumerate(cfg.COMMUNITIES):
        min_dist = float('inf')
        for st_info in results_dict['stations_info']:
            for item in st_info['covered']:
                if item['community'] == comm:
                    dist = item['distance']
                    if dist < min_dist:
                        min_dist = dist
        
        if min_dist == float('inf'):
            min_dist = 9999
        
        elderly_struct = cfg.ELDERLY_BY_TYPE_Y5[comm]
        
        for group in ['自理', '半失能', '失能']:
            count = elderly_struct[group]
            distance_by_type[group]['count'] += count
            distance_by_type[group]['weighted_dist'] += min_dist * count
            
            if min_dist <= 1000:
                distance_by_type[group]['covered'] += count
            else:
                distance_by_type[group]['blind'] += count
    
    for group in ['自理', '半失能', '失能']:
        info = distance_by_type[group]
        avg_dist = info['weighted_dist'] / info['count'] if info['count'] > 0 else 0
        coverage_rate = info['covered'] / info['count'] * 100 if info['count'] > 0 else 0
        blind_rate = info['blind'] / info['count'] * 100 if info['count'] > 0 else 0
        
        geographic_metrics[group] = {
            'avg_distance': avg_dist,
            'coverage_rate': coverage_rate,
            'blind_rate': blind_rate
        }
    
    information_metrics = {'scenario_A': {}, 'scenario_B': {}}
    
    for scenario, metrics_list, key in [
        ('A', results_dict['metrics_sub'], 'scenario_A'),
        ('B', results_dict['metrics_nosub'], 'scenario_B')
    ]:
        total_utilization = 0.0
        total_s2_score = 0.0
        station_count = len(metrics_list)
        
        for metrics in metrics_list:
            util = metrics['utilization']
            s2 = cfg.satisfaction_S2(util / 100.0)
            total_utilization += util
            total_s2_score += s2
        if station_count > 0:
            information_metrics[key]['avg_utilization'] = total_utilization / station_count
            information_metrics[key]['avg_s2_score'] = total_s2_score / station_count
        else:
            information_metrics[key]['avg_utilization'] = 0.0
            information_metrics[key]['avg_s2_score'] = 0.0
    
    table_data = []
    
    for group in ['失能', '半失能', '自理']:
        actual_A = economic_metrics['scenario_A']['actual'][group] * 100
        actual_B = economic_metrics['scenario_B']['actual'][group] * 100
        actual_release = actual_B - actual_A
        
        table_data.append({
            '可及性维度': '经济',
            '评价指标': f'实际支出占比（{group}老人，含满意度折扣）',
            '场景A（有补贴）': f'{actual_A:.2f}%',
            '场景B（无补贴）': f'{actual_B:.2f}%',
            '差异量化分析': f'补贴释放{actual_release:.2f}%购买力'
        })
        
        theory_A = economic_metrics['scenario_A']['theory'][group] * 100
        theory_B = economic_metrics['scenario_B']['theory'][group] * 100
        theory_release = theory_B - theory_A
        
        table_data.append({
            '可及性维度': '经济',
            '评价指标': f'理论刚需占比（{group}老人，假设100%满足）',
            '场景A（有补贴）': f'{theory_A:.2f}%',
            '场景B（无补贴）': f'{theory_B:.2f}%',
            '差异量化分析': f'补贴释放{theory_release:.2f}%刚需购买力'
        })
        
        suppression_A = (theory_A - actual_A) / theory_A * 100 if theory_A > 0 else 0
        suppression_B = (theory_B - actual_B) / theory_B * 100 if theory_B > 0 else 0
        suppression_change = suppression_B - suppression_A
        
        table_data.append({
            '可及性维度': '经济',
            '评价指标': f'消费抑制率（{group}老人，高价导致需求萎缩）',
            '场景A（有补贴）': f'{suppression_A:.2f}%',
            '场景B（无补贴）': f'{suppression_B:.2f}%',
            '差异量化分析': f'补贴使消费抑制降低{suppression_change:.2f}%'
        })
    
    avg_dist_A = sum(geographic_metrics[g]['avg_distance'] for g in ['自理', '半失能', '失能']) / 3
    avg_dist_B = avg_dist_A
    coverage_A = sum(geographic_metrics[g]['coverage_rate'] for g in ['自理', '半失能', '失能']) / 3
    coverage_B = coverage_A
    
    blind_A = sum(geographic_metrics[g]['blind_rate'] for g in ['自理', '半失能', '失能']) / 3
    blind_B = blind_A
    
    table_data.append({
        '可及性维度': '地理',
        '评价指标': '加权平均服务距离',
        '场景A（有补贴）': f'{avg_dist_A:.2f}米',
        '场景B（无补贴）': f'{avg_dist_B:.2f}米',
        '差异量化分析': '站点布局固定，距离无变化'
    })
    
    table_data.append({
        '可及性维度': '地理',
        '评价指标': '有效覆盖率（≤1000米）',
        '场景A（有补贴）': f'{coverage_A:.2f}%',
        '场景B（无补贴）': f'{coverage_B:.2f}%',
        '差异量化分析': '覆盖率由选址决定，与补贴无关'
    })
    
    table_data.append({
        '可及性维度': '地理',
        '评价指标': '覆盖盲区占比（>1000米）',
        '场景A（有补贴）': f'{blind_A:.2f}%',
        '场景B（无补贴）': f'{blind_B:.2f}%',
        '差异量化分析': '盲区比例固定，需优化选址'
    })
    
    # 信息可及性
    util_A = information_metrics['scenario_A']['avg_utilization']
    util_B = information_metrics['scenario_B']['avg_utilization']
    s2_A = information_metrics['scenario_A']['avg_s2_score']
    s2_B = information_metrics['scenario_B']['avg_s2_score']
    
    table_data.append({
        '可及性维度': '信息',
        '评价指标': '设施日均利用率',
        '场景A（有补贴）': f'{util_A:.2f}%',
        '场景B（无补贴）': f'{util_B:.2f}%',
        '差异量化分析': f'补贴使利用率{"提升" if util_A > util_B else "下降"}{abs(util_A - util_B):.2f}%'
    })
    
    table_data.append({
        '可及性维度': '信息',
        '评价指标': '响应满意度得分（S2）',
        '场景A（有补贴）': f'{s2_A:.4f}',
        '场景B（无补贴）': f'{s2_B:.4f}',
        '差异量化分析': f'S2得分{"改善" if s2_A > s2_B else "恶化"}{abs(s2_A - s2_B):.4f}'
    })
    
    df_accessibility = pd.DataFrame(table_data)
    
    return df_accessibility, {
        'economic': economic_metrics,
        'geographic': geographic_metrics,
        'information': information_metrics
    }

#结果分析
def export_to_excel(results_dict):

    excel_path = os.path.join(OUT_DIR, "服务定价补贴优化结果.xlsx")
    
    df_accessibility, detailed_metrics = calculate_quantitative_accessibility(results_dict)
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        
        model_overview = {
            '项目': [
                '目标函数',
                '决策变量',
                '约束条件1',
                '约束条件2',
                '约束条件3',
                '约束条件4',
                '约束条件5',
                '参数说明1',
                '参数说明2',
                '参数说明3',
                '参数说明4',
                '数据来源'
            ],
            '内容': [
                '最大化老人综合满意度 S = 0.2×S₁(距离) + 0.3×S₂(拥挤度) + 0.5×S₃(价格)',
                '各服务站6项服务的定价 pⱼ (元/次)，i=服务站编号, j=服务项目',
                '利润率约束：利润率 ≤ 8%（利润率 = (服务利润+补贴-运营成本)/运营成本）',
                '补贴上限：小型站1000元/日，中型站1800元/日，大型站2600元/日',
                '紧急救助免费：p_紧急救助 = 0 元/次',
                '定价非负：pⱼ ≥ 0',
                '补贴范围：除紧急救助外的5项服务，按实际有效服务人次补贴2元/人次',
                '年运营成本：小型站739,000元，中型站1,168,000元，大型站1,606,000元',
                '补贴标准：2元/人次（前5项服务）',
                '服务满意度权重：距离0.2、拥挤度0.3、价格0.5',
                '需求数据：基于问题1人口预测第5年末数据，附件2人均月度需求',
                '假设说明：所有数据来源于题目附件1-5及问题1/2求解结果'
            ]
        }
        df_model = pd.DataFrame(model_overview)
        df_model.to_excel(writer, sheet_name='优化模型概述', index=False)
        
        pricing_rows = []
        for st_info, prices in zip(results_dict['stations_info'], results_dict['optimal_prices_sub']):
            for svc_idx, svc_name in enumerate(cfg.SERVICES):
                pricing_rows.append({
                    '服务站编号': st_info['name'],
                    '服务站类型': st_info['type'],
                    '服务项目': svc_name,
                    '最优定价(元/次)': round(prices[svc_idx], 2)
                })
        df_pricing = pd.DataFrame(pricing_rows)
        df_pricing.to_excel(writer, sheet_name='最优定价', index=False)
        
        profit_rows = []
        for st_info, metrics in zip(results_dict['stations_info'], results_dict['metrics_sub']):
            margin_pct = metrics['margin'] * 100
            meets_constraint = '是' if 0 <= metrics['margin'] <= cfg.PROFIT_MARGIN_MAX else '否'
            profit_rows.append({
                '服务站编号': st_info['name'],
                '年运营成本(元)': round(st_info['annual_operating_cost'], 2),
                '年服务总收入(元)': round(metrics['annual_revenue'], 2),
                '年政府补贴(元)': round(metrics['annual_subsidy'], 2),
                '年总利润(元)': round(metrics['profit'], 2),
                '利润率(%)': round(margin_pct, 2),
                '满足8%约束': meets_constraint
            })
        df_profit = pd.DataFrame(profit_rows)
        df_profit.to_excel(writer, sheet_name='服务站利润与利润率', index=False)
        
        satisfaction_rows = []
        for comm in cfg.COMMUNITIES:
            for elderly_type in ['自理', '半失能', '失能']:
                # 查找该小区所属服务站
                assigned_station = None
                for st_info in results_dict['stations_info']:
                    if comm in [item['community'] for item in st_info['covered']]:
                        assigned_station = st_info['name']
                        break
                
                if assigned_station and assigned_station in results_dict['satisfaction_data']:
                    comm_data = results_dict['satisfaction_data'][assigned_station]['details'].get(comm, {})
                    avg_s = comm_data.get('avg_s', 0.0)
                    avg_s3 = comm_data.get('avg_s3', 0.0)
                    other_dims = round(avg_s * 0.5 + avg_s3 * 0.5, 4)
                else:
                    avg_s = 0.0
                    avg_s3 = 0.0
                    other_dims = '-'
                
                satisfaction_rows.append({
                    '小区编号': comm,
                    '老人类型': elderly_type,
                    '综合满意度得分': round(avg_s, 4),
                    '价格满意度得分': round(avg_s3, 4),
                    '其他维度得分': other_dims if isinstance(other_dims, str) else round(other_dims, 4)
                })
        df_satisfaction = pd.DataFrame(satisfaction_rows)
        df_satisfaction.to_excel(writer, sheet_name='小区满意度得分', index=False)

        constraint_rows = []
        
        # 利润率约束
        for st_info, metrics in zip(results_dict['stations_info'], results_dict['metrics_sub']):
            margin_pct = metrics['margin'] * 100
            constraint_rows.append({
                '约束条件': f"服务站{st_info['name']}利润率",
                '要求': '≤ 8%',
                '实际值': f"{margin_pct:.2f}%",
                '是否满足': '是' if 0 <= metrics['margin'] <= cfg.PROFIT_MARGIN_MAX else '否'
            })
        
        # 补贴上限约束
        for st_info, metrics in zip(results_dict['stations_info'], results_dict['metrics_sub']):
            daily_subsidy = metrics['annual_subsidy'] / 365
            station_type = st_info['type']
            type_map = {'小型': 1, '中型': 2, '大型': 3}
            type_key = type_map[station_type]
            daily_cap = cfg.DAILY_SUBSIDY_CAP[type_key]
            constraint_rows.append({
                '约束条件': f"服务站{st_info['name']}日补贴上限({station_type})",
                '要求': f'≤ {daily_cap}元/日',
                '实际值': f'{daily_subsidy:.2f}元/日',
                '是否满足': '是' if daily_subsidy <= daily_cap + 0.01 else '否'
            })
        
        # 紧急救助免费
        for st_info, prices in zip(results_dict['stations_info'], results_dict['optimal_prices_sub']):
            emergency_price = prices[5]
            constraint_rows.append({
                '约束条件': f"服务站{st_info['name']}紧急救助定价",
                '要求': '= 0元/次',
                '实际值': f'{emergency_price:.2f}元/次',
                '是否满足': '是' if emergency_price == 0.0 else '否'
            })
        
        # 定价非负
        for st_info, prices in zip(results_dict['stations_info'], results_dict['optimal_prices_sub']):
            min_price = np.min(prices[:5])
            constraint_rows.append({
                '约束条件': f"服务站{st_info['name']}定价非负",
                '要求': '≥ 0元/次',
                '实际值': f'{min_price:.2f}元/次',
                '是否满足': '是' if min_price >= 0 else '否'
            })
        
        df_constraints = pd.DataFrame(constraint_rows)
        df_constraints.to_excel(writer, sheet_name='约束满足情况汇总', index=False)
        
        df_accessibility.to_excel(writer, sheet_name='可及性影响分析', index=False)
        
        detail_data = []
        
        # 经济可及性详情
        for scenario_name, scenario_key in [('有补贴', 'scenario_A'), ('无补贴', 'scenario_B')]:
            for group in ['自理', '半失能', '失能']:
                detail_data.append({
                    '维度': '经济可及性',
                    '场景': scenario_name,
                    '老人类型': group,
                    '指标': '实际支出占比（含满意度折扣）',
                    '数值': f"{detailed_metrics['economic'][scenario_key]['actual'][group] * 100:.2f}%"
                })
                detail_data.append({
                    '维度': '经济可及性',
                    '场景': scenario_name,
                    '老人类型': group,
                    '指标': '理论刚需占比（100%满足）',
                    '数值': f"{detailed_metrics['economic'][scenario_key]['theory'][group] * 100:.2f}%"
                })
        
        # 地理可及性详情
        for group in ['自理', '半失能', '失能']:
            geo = detailed_metrics['geographic'][group]
            detail_data.append({
                '维度': '地理可及性',
                '场景': '双场景相同',
                '老人类型': group,
                '指标': '加权平均距离',
                '数值': f"{geo['avg_distance']:.2f}米"
            })
            detail_data.append({
                '维度': '地理可及性',
                '场景': '双场景相同',
                '老人类型': group,
                '指标': '有效覆盖率',
                '数值': f"{geo['coverage_rate']:.2f}%"
            })
        
        # 信息可及性详情
        for scenario_name, scenario_key in [('有补贴', 'scenario_A'), ('无补贴', 'scenario_B')]:
            info = detailed_metrics['information'][scenario_key]
            detail_data.append({
                '维度': '信息可及性',
                '场景': scenario_name,
                '老人类型': '全体',
                '指标': '设施利用率',
                '数值': f"{info['avg_utilization']:.2f}%"
            })
            detail_data.append({
                '维度': '信息可及性',
                '场景': scenario_name,
                '老人类型': '全体',
                '指标': '响应满意度S2',
                '数值': f"{info['avg_s2_score']:.4f}"
            })
        
        df_detail = pd.DataFrame(detail_data)
        df_detail.to_excel(writer, sheet_name='可及性详细数据', index=False)
        
        # 调整列宽（美化）
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column_cells in worksheet.columns:
                max_length = 0
                column = column_cells[0].column_letter
                for cell in column_cells:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 70)
                worksheet.column_dimensions[column].width = adjusted_width
    
    print(f"\n✓ Excel结果已保存至: {excel_path}")
    print(f"✓ 双轨可及性分析已完成（实际支出 + 理论刚需）")
    return excel_path



def main():
    print("=" * 60)
    print(" 嵌入式社区养老服务站定价模型求解系统")
    print("=" * 60)

    valid_stations = [st for st in cfg.STATIONS if len(st.get('covered', [])) > 0]

    if not valid_stations:
        print("错误：未在 config3.py 中找到任何有效的建站覆盖信息！")
        return

    stations_info = []
    optimal_prices_sub = []
    optimal_prices_nosub = []
    metrics_sub_list = []
    metrics_nosub_list = []
    satisfaction_data = {}

    for st in valid_stations:
        name = st['name']
        print(f"-> 正在精确求解服务站 [{name}] 双场景定价平衡模型...")

        # 1. 场景A（有补贴）
        opt_p_sub = optimize_station_prices(st, use_subsidy=True)
        opt_p_sub[5] = 0.0
        metrics_sub = get_station_metrics(opt_p_sub, st, use_subsidy=True)
        
        stations_info.append(st)
        optimal_prices_sub.append(opt_p_sub)
        metrics_sub_list.append(metrics_sub)
        satisfaction_data[name] = metrics_sub

        # 2. 场景B（无补贴，用于对比分析）
        opt_p_nosub = optimize_station_prices(st, use_subsidy=False)
        opt_p_nosub[5] = 0.0
        metrics_nosub = get_station_metrics(opt_p_nosub, st, use_subsidy=False)
        optimal_prices_nosub.append(opt_p_nosub)
        metrics_nosub_list.append(metrics_nosub)

    # 构建结果字典
    results_dict = {
        'stations_info': stations_info,
        'optimal_prices_sub': optimal_prices_sub,
        'optimal_prices_nosub': optimal_prices_nosub,
        'metrics_sub': metrics_sub_list,
        'metrics_nosub': metrics_nosub_list,
        'satisfaction_data': satisfaction_data
    }

    export_to_excel(results_dict)
    
    df_accessibility, detailed_metrics = calculate_quantitative_accessibility(results_dict)
    results_dict['economic_metrics'] = detailed_metrics['economic']
    results_dict['info_metrics'] = detailed_metrics['information']
    results_dict['geographic_metrics'] = detailed_metrics['geographic']
    
    generate_visualizations(results_dict, OUT_DIR)
    


    print("\n" + "=" * 25 + " 求解完成，结果已导出！ " + "=" * 25)


if __name__ == "__main__":
    main()
