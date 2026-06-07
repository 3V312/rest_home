import os
import math
import pandas as pd
from datetime import datetime
import config1 as cfg


def calc_p1():
    p_hist = []
    curr = {k: [float(v[2]), float(v[3]), float(v[4])] for k, v in cfg.C_DATA.items()}

    for yr in range(1, 6):
        for c in cfg.C_DATA:
            s, h, d = curr[c]
            n = s + h + d

            s_n = s * (1 - cfg.P_12 - cfg.DIE_R) + cfg.NEW_R * n
            h_n = h * (1 - cfg.P_23 - cfg.DIE_R) + s * cfg.P_12
            d_n = d * (1 - cfg.DIE_R) + h * cfg.P_23

            curr[c] = [s_n, h_n, d_n]

            p_hist.append([
                f'第{yr}年末', c,
                math.ceil(s_n), math.ceil(h_n), math.ceil(d_n), math.ceil(s_n + h_n + d_n)
            ])

    df11 = pd.DataFrame(p_hist, columns=['年份', '小区', '自理人数', '半失能人数', '失能人数', '总老人数'])

    res12, res13 = [], []

    cost_s = sum(f * p for f, p in zip(cfg.F_S, cfg.PRICES))
    cost_h = sum(f * p for f, p in zip(cfg.F_H, cfg.PRICES))
    cost_d = sum(f * p for f, p in zip(cfg.F_D, cfg.PRICES))

    for c, vals in cfg.C_DATA.items():
        inc = vals[5]
        s_5, h_5, d_5 = curr[c]

        a_s = min(1.0, (inc * cfg.LIMITS[0]) / cost_s) if cost_s > 0 else 1.0
        a_h = min(1.0, (inc * cfg.LIMITS[1]) / cost_h) if cost_h > 0 else 1.0
        a_d = min(1.0, (inc * cfg.LIMITS[2]) / cost_d) if cost_d > 0 else 1.0

        for idx, name in enumerate(cfg.SVCS):
            t_s = s_5 * cfg.F_S[idx]
            t_h = h_5 * cfg.F_H[idx]
            t_d = d_5 * cfg.F_D[idx]
            res12.append([
                c, name,
                math.ceil(t_s), math.ceil(t_h), math.ceil(t_d), math.ceil(t_s + t_h + t_d)
            ])

            act_s = t_s * a_s
            act_h = t_h * a_h
            act_d = t_d * a_d
            res13.append([
                c, name,
                math.ceil(act_s), math.ceil(act_h), math.ceil(act_d), math.ceil(act_s + act_h + act_d)
            ])

    df12 = pd.DataFrame(res12,
                        columns=['小区', '服务项目', '自理理论需求', '半失能理论需求', '失能理论需求', '总量理论需求'])
    df13 = pd.DataFrame(res13,
                        columns=['小区', '服务项目', '自理实际需求', '半失能实际需求', '失能实际需求', '总量实际需求'])

    path = r"D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem1\results"
    os.makedirs(path, exist_ok=True)

    ts = datetime.now().strftime("%m%d_%H%M%S")
    out = os.path.join(path, f"1_{ts}.xlsx")

    with pd.ExcelWriter(out) as w:
        df11.to_excel(w, sheet_name='1.1人口预测', index=False)
        df12.to_excel(w, sheet_name='1.2理论需求', index=False)
        df13.to_excel(w, sheet_name='1.3实际需求', index=False)

    print(f"saved successfully: {out}")


if __name__ == '__main__':
    calc_p1()