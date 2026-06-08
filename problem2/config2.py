# config2.py
# 问题2：服务站选址与规模化优化 - 原始配置

import os
import sys
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_config import (
    COMMUNITIES, DIST_MATRIX, SERVICES, BASE_PRICE, REVENUE_PER_SERVICE, COST_PER_SERVICE,
    ELDERLY_BY_TYPE_Y5, TOTAL_ELDERLY_Y5, DEMAND_MONTHLY, DAILY_DEMAND, DAILY_DEMAND_BY_SERVICE,
    INCOME_PER_MONTH, CONSUMPTION_CAP_RATIO, SERVICE_RADIUS,
    CONSTRUCTION_COST, DAILY_MANAGEMENT_COST, MAX_CAPACITY,
    W1, W2, W3,
    satisfaction_S1, satisfaction_S2, satisfaction_S3, total_satisfaction,
    get_distance, get_service_index, get_base_price_by_service
)

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

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



BUDGET_MAX = 120

# 总建设预算（万元，原始值）
BUDGET_MAX = 120



BASE_PRICES = REVENUE_PER_SERVICE

def calc_s1(d):
    return satisfaction_S1(d)

def calc_s2(utilization):
    return satisfaction_S2(utilization)

def calc_s3(price, base_price):
    return satisfaction_S3(price, base_price)

def calc_community_s3(comm_idx):
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
            weighted_s3 += weight * satisfaction_S3(price, base_price)
    return weighted_s3

def calc_satisfaction(distance):
    s1 = satisfaction_S1(distance)
    return W1 * s1 + W2 * 1.0 + W3 * 1.0

def calc_satisfaction_dynamic(d, utilization, s3=1.0):
    s1 = satisfaction_S1(d)
    s2 = satisfaction_S2(utilization)
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