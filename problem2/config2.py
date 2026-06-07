# config2.py
# 问题2：服务站选址与规模化优化 - 原始配置

import os
import numpy as np
from datetime import datetime

# ================== 基础目录 ==================
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# ================== 小区基础数据（第5年末，原始预测） ==================
COMMUNITIES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

# 第5年末各类老年人口 [自理, 半失能, 失能, 总]（原始参数：增长率7%，P_12=0.045, P_23=0.1）
ELDERLY_POP_YEAR5 = {
    'A': [550, 168, 132, 850],
    'B': [460, 142, 122, 724],
    'C': [705, 218, 172, 1095],
    'D': [415, 128, 108, 651],
    'E': [602, 185, 148, 935],
    'F': [368, 112, 85, 565],
    'G': [665, 204, 162, 1031],
    'H': [440, 135, 104, 679],
    'I': [568, 176, 138, 882],
    'J': [510, 155, 120, 785]
}

# 各小区老年人口总数（用于覆盖率计算）
ELDERLY_POP = [ELDERLY_POP_YEAR5[comm][3] for comm in COMMUNITIES]
TOTAL_ELDERLY = sum(ELDERLY_POP)

# 分类型老年人口（按小区顺序）
ELDERLY_POP_S = [ELDERLY_POP_YEAR5[comm][0] for comm in COMMUNITIES]  # 自理
ELDERLY_POP_H = [ELDERLY_POP_YEAR5[comm][1] for comm in COMMUNITIES]  # 半失能
ELDERLY_POP_D = [ELDERLY_POP_YEAR5[comm][2] for comm in COMMUNITIES]  # 失能

# ================== 需求数据（原始第5年末需求） ==================
DEMAND_MONTHLY_TOTAL = {
    'A': [12455, 8048, 2105, 2237, 702, 528],
    'B': [10352, 6688, 1748, 1860, 583, 440],
    'C': [16460, 10708, 2942, 2995, 981, 735],
    'D': [9009, 5789, 1449, 1603, 483, 369],
    'E': [13819, 8963, 2410, 2500, 803, 602],
    'F': [7601, 4840, 1124, 1330, 375, 291],
    'G': [15305, 9938, 2695, 2775, 898, 674],
    'H': [9528, 6114, 1515, 1690, 505, 384],
    'I': [12837, 8298, 2178, 2307, 726, 544],
    'J': [11287, 7268, 1852, 2014, 617, 466]
}

# 各小区每日总需求（人次/日）= 月度总需求 / 30
DAILY_DEMAND = [sum(DEMAND_MONTHLY_TOTAL[comm]) / 30 for comm in COMMUNITIES]

# 各小区分服务日需求（6项服务，单位：次/日）
DAILY_DEMAND_BY_SERVICE = {
    comm: [d / 30 for d in DEMAND_MONTHLY_TOTAL[comm]] for comm in COMMUNITIES
}

# ================== 距离矩阵（附件4，单位：米） ==================
DIST_MATRIX = [
    [0,   600, 1200, 900, 1500, 1800, 1300, 700, 1100, 500],
    [600, 0,   800, 500, 1100, 1400, 900, 400, 700,  300],
    [1200,800, 0,   700, 600,  900,  500, 900, 600,  700],
    [900, 500, 700, 0,   800,  1100, 600, 300, 500,  400],
    [1500,1100,600, 800, 0,    500,  400, 1000,500,  800],
    [1800,1400,900, 1100,500, 0,    500, 1200,700,  1100],
    [1300,900, 500, 600, 400,  500,  0,   800, 400,  600],
    [700, 400, 900, 300, 1000, 1200, 800, 0,   600,  300],
    [1100,700, 600, 500, 500,  700,  400, 600, 0,    400],
    [500, 300, 700, 400, 800,  1100, 600, 300, 400,  0]
]

# ================== 服务站参数（附件3，原始配置） ==================
# 类型编码：0-不建, 1-小型, 2-中型, 3-大型
CONSTRUCTION_COST = {0: 0, 1: 18, 2: 32, 3: 45}      # 万元

# 日固定管理成本（元/日）- 原始值
DAILY_MANAGEMENT_COST = {0: 0, 1: 2000, 2: 3200, 3: 4400}

# 日服务能力（人次/日）
MAX_CAPACITY = {0: 0, 1: 1000, 2: 2000, 3: 3000}

SERVICE_RADIUS = 1000   # 米

# 总建设预算（万元，原始值）
BUDGET_MAX = 120

# ================== 服务项目配置（附件2） ==================
SERVICES = ['助餐', '日间照料', '上门护理', '康复理疗', '助浴', '紧急救助']
REVENUE_PER_SERVICE = [10, 20, 30, 28, 25, 0]   # 元/次（服务收入）
COST_PER_SERVICE = [8, 16, 24, 23, 20, 8]       # 元/次（直接支出成本）

# ================== 满意度函数（附件5） ==================
W1, W2, W3 = 0.2, 0.3, 0.5   # 距离、响应、价格满意度权重

# 服务基准价格（用于价格满意度计算）
BASE_PRICES = [10, 20, 30, 28, 25, 0]   # 与REVENUE_PER_SERVICE一致

def calc_s1(d):
    """距离满意度 S1（分段线性）"""
    if d <= 300:
        return 1.00
    elif d <= 500:
        return 1.0 - (d - 300) / 200 * 0.1
    elif d <= 650:
        return 0.9 - (d - 500) / 150 * 0.15
    elif d <= 1000:
        return 0.75 - (d - 650) / 350 * 0.15
    else:
        return 0.0

def calc_s2(utilization):
    """服务响应满意度 S2（平滑版本）"""
    if utilization <= 0.60:
        return 1.00
    elif utilization <= 0.75:
        return 1.0 - (utilization - 0.60) / 0.15 * 0.07
    elif utilization <= 0.85:
        return 0.93 - (utilization - 0.75) / 0.10 * 0.08
    elif utilization <= 0.95:
        return 0.85 - (utilization - 0.85) / 0.10 * 0.13
    elif utilization <= 1.00:
        return 0.72 - (utilization - 0.95) / 0.05 * 0.12
    else:
        return max(0.4, 0.6 - (utilization - 1.0) * 0.4)

def calc_s3(price, base_price):
    """价格满意度 S3（基于价格与基准价的比值）"""
    if base_price == 0:
        return 1.0
    ratio = price / base_price
    if ratio <= 0.8:
        return 1.00
    elif ratio <= 1.0:
        return 1.0 - (ratio - 0.8) / 0.2 * 0.1
    elif ratio <= 1.2:
        return 0.9 - (ratio - 1.0) / 0.2 * 0.15
    elif ratio <= 1.5:
        return 0.75 - (ratio - 1.2) / 0.3 * 0.15
    else:
        return 0.6

def calc_community_s3(comm_idx):
    """计算小区 i 的价格满意度 S3i（按服务使用量加权平均）"""
    comm_name = COMMUNITIES[comm_idx]
    daily_demands = DAILY_DEMAND_BY_SERVICE[comm_name]
    total_demand = sum(daily_demands)
    if total_demand == 0:
        return 1.0
    weighted_s3 = 0.0
    for svc_idx, demand in enumerate(daily_demands):
        if demand > 0:
            weight = demand / total_demand
            price = REVENUE_PER_SERVICE[svc_idx]
            base_price = BASE_PRICES[svc_idx]
            weighted_s3 += weight * calc_s3(price, base_price)
    return weighted_s3

def calc_satisfaction(distance):
    """简化满意度（默认S2=1.0, S3=1.0），用于静态计算"""
    s1 = calc_s1(distance)
    return W1 * s1 + W2 * 1.0 + W3 * 1.0

def calc_satisfaction_dynamic(d, utilization, s3=1.0):
    """动态综合满意度（考虑拥挤度和价格满意度）"""
    s1 = calc_s1(d)
    s2 = calc_s2(utilization)
    return W1 * s1 + W2 * s2 + W3 * s3

# ================== 利润计算辅助函数 ==================
def calc_station_profit(station_idx, covered_communities, allocation, station_loads, stations):
    """计算单个服务站的年度利润（单位：元）"""
    capacity = stations[station_idx]
    station_type = 0
    for stype, cap in MAX_CAPACITY.items():
        if cap == capacity:
            station_type = stype
            break

    theoretical_demand = sum(DAILY_DEMAND[comm_idx] for comm_idx in covered_communities)
    if theoretical_demand > capacity and theoretical_demand > 0:
        truncation_factor = capacity / theoretical_demand
    else:
        truncation_factor = 1.0

    annual_revenue = 0
    for comm_idx in covered_communities:
        comm_name = COMMUNITIES[comm_idx]
        daily_demands = DAILY_DEMAND_BY_SERVICE[comm_name]
        for svc_idx, demand in enumerate(daily_demands):
            actual_demand = demand * truncation_factor
            annual_revenue += actual_demand * REVENUE_PER_SERVICE[svc_idx] * 365

    constr_cost_yuan = CONSTRUCTION_COST[station_type] * 10000
    annual_dep = constr_cost_yuan / 20
    annual_mgmt = DAILY_MANAGEMENT_COST[station_type] * 365

    annual_direct = 0
    for comm_idx in covered_communities:
        comm_name = COMMUNITIES[comm_idx]
        daily_demands = DAILY_DEMAND_BY_SERVICE[comm_name]
        for svc_idx, demand in enumerate(daily_demands):
            actual_demand = demand * truncation_factor
            annual_direct += actual_demand * COST_PER_SERVICE[svc_idx] * 365

    annual_expense = annual_dep + annual_mgmt + annual_direct
    annual_profit = annual_revenue - annual_expense
    return annual_revenue, annual_expense, annual_profit

def mds_projection(dist_matrix):
    """MDS投影，返回2D坐标"""
    n = len(dist_matrix)
    dist = np.array(dist_matrix, dtype=float)
    dist_sq = dist ** 2
    H = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * H @ dist_sq @ H
    eigenvalues, eigenvectors = np.linalg.eigh(B)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx[:2]]
    eigenvectors = eigenvectors[:, idx[:2]]
    eigenvalues = np.maximum(eigenvalues, 0)
    coords = eigenvectors * np.sqrt(eigenvalues)
    return coords

def get_out_dir(prefix="result"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(BASE_DIR, f"{prefix}_{ts}")
    os.makedirs(path, exist_ok=True)
    return path