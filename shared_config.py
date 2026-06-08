# -*- coding: utf-8 -*-
"""
共享配置模块
提取 problem2/config2.py 和 problem3/config3.py 中的公共数据和函数
"""

import numpy as np

COMMUNITIES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

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

SERVICES = ['助餐', '日间照料', '上门护理', '康复理疗', '助浴', '紧急救助']
SERVICE_INDEX = {name: idx for idx, name in enumerate(SERVICES)}

BASE_PRICE = [8, 16, 24, 23, 20, 8]
REVENUE_PER_SERVICE = [10, 20, 30, 28, 25, 0]
COST_PER_SERVICE = [8, 16, 24, 23, 20, 8]

ELDERLY_BY_TYPE_Y5 = {
    'A': {'自理': 550, '半失能': 168, '失能': 132},
    'B': {'自理': 460, '半失能': 142, '失能': 122},
    'C': {'自理': 705, '半失能': 218, '失能': 172},
    'D': {'自理': 415, '半失能': 128, '失能': 108},
    'E': {'自理': 602, '半失能': 185, '失能': 148},
    'F': {'自理': 368, '半失能': 112, '失能': 85},
    'G': {'自理': 665, '半失能': 204, '失能': 162},
    'H': {'自理': 440, '半失能': 135, '失能': 104},
    'I': {'自理': 568, '半失能': 176, '失能': 138},
    'J': {'自理': 510, '半失能': 155, '失能': 120}
}

TOTAL_ELDERLY_Y5 = {comm: sum(data.values()) for comm, data in ELDERLY_BY_TYPE_Y5.items()}

DEMAND_MONTHLY = {
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

DEMAND_YEARLY = {comm: [d * 12 for d in DEMAND_MONTHLY[comm]] for comm in DEMAND_MONTHLY}

DAILY_DEMAND_BY_SERVICE = {
    comm: [d / 30 for d in DEMAND_MONTHLY[comm]] for comm in COMMUNITIES
}

DAILY_DEMAND = [sum(DEMAND_MONTHLY[comm]) / 30 for comm in COMMUNITIES]

INCOME_PER_MONTH = {
    'A': 3400, 'B': 3100, 'C': 3800, 'D': 2900, 'E': 3500,
    'F': 2700, 'G': 3600, 'H': 3000, 'I': 3300, 'J': 3200
}

CONSUMPTION_CAP_RATIO = {'自理': 0.20, '半失能': 0.25, '失能': 0.30}

SERVICE_RADIUS = 1000

CONSTRUCTION_COST = {0: 0, 1: 18, 2: 32, 3: 45}
DAILY_MANAGEMENT_COST = {0: 0, 1: 2000, 2: 3200, 3: 4400}
MAX_CAPACITY = {0: 0, 1: 1000, 2: 2000, 3: 3000}

W1, W2, W3 = 0.2, 0.3, 0.5

def satisfaction_S1(distance_m):
    """距离满意度 S1（分段函数）"""
    if distance_m <= 300:
        return 1.00
    elif distance_m <= 500:
        return 0.90
    elif distance_m <= 650:
        return 0.75
    elif distance_m <= 1000:
        return 0.60
    else:
        return 0.0

def satisfaction_S2(utilization):
    """服务响应满意度 S2（基于利用率）"""
    if utilization <= 0.60:
        return 1.00
    elif utilization <= 0.75:
        return 0.93
    elif utilization <= 0.85:
        return 0.85
    elif utilization <= 0.95:
        return 0.72
    else:
        return 0.60

def satisfaction_S3(price, base_price):
    """价格满意度 S3"""
    if base_price == 0:
        return 1.0
    ratio = price / base_price
    if ratio <= 0.8:
        return 1.00
    elif ratio <= 1.0:
        return 1.0 - (ratio - 0.8) / 0.2 * 0.1
    elif ratio <= 1.2:
        return 0.9 - (ratio - 1.0) / 0.2 * 0.15
    else:
        return 0.60

def total_satisfaction(distance, price, base_price, utilization=0.5):
    """综合满意度计算"""
    s1 = satisfaction_S1(distance)
    s2 = satisfaction_S2(utilization)
    s3 = satisfaction_S3(price, base_price)
    return W1 * s1 + W2 * s2 + W3 * s3

def get_distance(comm1, comm2):
    """获取两个小区之间的距离"""
    i = COMMUNITIES.index(comm1)
    j = COMMUNITIES.index(comm2)
    return DIST_MATRIX[i][j]

def get_service_index(service_name):
    """获取服务索引"""
    return SERVICE_INDEX[service_name]

def get_base_price_by_service(service_name):
    """获取服务基准价格"""
    return BASE_PRICE[get_service_index(service_name)]