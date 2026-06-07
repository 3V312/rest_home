import os
import numpy as np
from datetime import datetime

SERVICES = ['助餐', '日间照料', '上门护理', '康复理疗', '助浴', '紧急救助']
SERVICE_INDEX = {name: idx for idx, name in enumerate(SERVICES)}

BASE_PRICE = [8, 16, 24, 23, 20, 8]
REVENUE = [10, 20, 30, 28, 25, 0]

CONSUMPTION_CAP_RATIO = {'自理': 0.20, '半失能': 0.25, '失能': 0.30}

SUBSIDY_PER_SERVICE = 2.0
DAILY_SUBSIDY_CAP = {1: 1000, 2: 1800, 3: 2600}

def get_annual_subsidy_cap(station_type):
    daily = DAILY_SUBSIDY_CAP[station_type]
    return daily * 365

PROFIT_MARGIN_MAX = 0.08

DAILY_FIXED_COST_SMALL = 2000
CONSTRUCTION_COST_SMALL = 180000
ANNUAL_DEPRECIATION_SMALL = CONSTRUCTION_COST_SMALL / 20
ANNUAL_OPERATING_COST_SMALL = DAILY_FIXED_COST_SMALL * 365 + ANNUAL_DEPRECIATION_SMALL

DAILY_FIXED_COST_MEDIUM = 3200
CONSTRUCTION_COST_MEDIUM = 320000
ANNUAL_DEPRECIATION_MEDIUM = CONSTRUCTION_COST_MEDIUM / 20
ANNUAL_OPERATING_COST_MEDIUM = DAILY_FIXED_COST_MEDIUM * 365 + ANNUAL_DEPRECIATION_MEDIUM

DAILY_FIXED_COST_LARGE = 4400
CONSTRUCTION_COST_LARGE = 450000
ANNUAL_DEPRECIATION_LARGE = CONSTRUCTION_COST_LARGE / 20
ANNUAL_OPERATING_COST_LARGE = DAILY_FIXED_COST_LARGE * 365 + ANNUAL_DEPRECIATION_LARGE

def get_annual_operating_cost(station_type):
    if station_type == '小型':
        return ANNUAL_OPERATING_COST_SMALL
    elif station_type == '中型':
        return ANNUAL_OPERATING_COST_MEDIUM
    elif station_type == '大型':
        return ANNUAL_OPERATING_COST_LARGE
    else:
        return 0

INCOME_PER_MONTH = {
    'A': 3400, 'B': 3100, 'C': 3800, 'D': 2900, 'E': 3500,
    'F': 2700, 'G': 3600, 'H': 3000, 'I': 3300, 'J': 3200
}

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

DEMAND_PER_CAPITA_MONTHLY = {
    '自理':   [14, 8, 0, 2, 0, 0.15],
    '半失能': [20, 14, 6, 4, 2, 1],
    '失能':   [22, 18, 12, 6, 4, 3]
}

DEMAND_BY_TYPE_MONTHLY = {
    'A': {
        '自理':   [7618, 4352, 0, 1088, 0, 81],
        '半失能': [2921, 2045, 876, 584, 292, 146],
        '失能':   [1828, 1489, 993, 496, 331, 248]
    },
    'B': {
        '自理':   [6308, 3605, 0, 901, 0, 68],
        '半失能': [2473, 1731, 742, 495, 248, 124],
        '失能':   [1558, 1276, 851, 425, 283, 212]
    },
    'C': {
        '自理':   [9728, 5559, 0, 1389, 0, 104],
        '半失能': [3784, 2649, 1131, 754, 378, 189],
        '失能':   [2888, 2358, 1572, 786, 524, 393]
    },
    'D': {
        '自理':   [5714, 3265, 0, 816, 0, 61],
        '半失能': [2221, 1555, 662, 441, 221, 110],
        '失能':   [1040, 848, 565, 283, 189, 142]
    },
    'E': {
        '自理':   [8306, 4746, 0, 1186, 0, 89],
        '半失能': [3219, 2253, 965, 643, 322, 161],
        '失能':   [2208, 1807, 1205, 602, 401, 301]
    },
    'F': {
        '自理':   [5065, 2899, 0, 725, 0, 54],
        '半失能': [1956, 1369, 587, 391, 196, 98],
        '失能':   [567, 463, 309, 154, 103, 77]
    },
    'G': {
        '自理':   [9128, 5228, 0, 1307, 0, 98],
        '半失能': [3537, 2476, 1061, 707, 354, 177],
        '失能':   [2513, 2054, 1369, 684, 456, 342]
    },
    'H': {
        '自理':   [6052, 3469, 0, 867, 0, 65],
        '半失能': [2359, 1651, 712, 475, 238, 119],
        '失能':   [1072, 875, 583, 292, 194, 146]
    },
    'I': {
        '自理':   [7848, 4485, 0, 1121, 0, 84],
        '半失能': [3066, 2146, 920, 614, 307, 153],
        '失能':   [1876, 1532, 1021, 510, 340, 255]
    },
    'J': {
        '自理':   [7030, 4017, 0, 1004, 0, 75],
        '半失能': [2702, 1892, 811, 541, 270, 135],
        '失能':   [1472, 1204, 803, 401, 267, 200]
    }
}

COMMUNITIES = ['A','B','C','D','E','F','G','H','I','J']

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

def get_distance(comm1, comm2):
    i = COMMUNITIES.index(comm1)
    j = COMMUNITIES.index(comm2)
    return DIST_MATRIX[i][j]

STATIONS = [
    {
        'name': 'C',
        'location': 'C',
        'type': '小型',
        'capacity_per_day': 1000,
        'annual_operating_cost': ANNUAL_OPERATING_COST_SMALL,
        'covered': [
            {'community': 'C', 'distance': get_distance('C','C')}
        ]
    },
    {
        'name': 'E',
        'location': 'E',
        'type': '中型',
        'capacity_per_day': 2000,
        'annual_operating_cost': ANNUAL_OPERATING_COST_MEDIUM,
        'covered': [
            {'community': 'E', 'distance': get_distance('E','E')},
            {'community': 'F', 'distance': get_distance('E','F')},
            {'community': 'G', 'distance': get_distance('E','G')}
        ]
    },
    {
        'name': 'H',
        'location': 'H',
        'type': '小型',
        'capacity_per_day': 1000,
        'annual_operating_cost': ANNUAL_OPERATING_COST_SMALL,
        'covered': [
            {'community': 'D', 'distance': get_distance('H','D')},
            {'community': 'H', 'distance': get_distance('H','H')}
        ]
    },
    {
        'name': 'J',
        'location': 'J',
        'type': '大型',
        'capacity_per_day': 3000,
        'annual_operating_cost': ANNUAL_OPERATING_COST_LARGE,
        'covered': [
            {'community': 'A', 'distance': get_distance('J','A')},
            {'community': 'B', 'distance': get_distance('J','B')},
            {'community': 'I', 'distance': get_distance('J','I')},
            {'community': 'J', 'distance': get_distance('J','J')}
        ]
    }
]

def satisfaction_S1(distance_m):
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
    s1 = satisfaction_S1(distance)
    s2 = satisfaction_S2(utilization)
    s3 = satisfaction_S3(price, base_price)
    return 0.2 * s1 + 0.3 * s2 + 0.5 * s3

def get_service_index(service_name):
    return SERVICE_INDEX[service_name]

def get_base_price_by_service(service_name):
    return BASE_PRICE[get_service_index(service_name)]
