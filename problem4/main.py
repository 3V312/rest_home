
import os
import json
import pandas as pd

OLD_RESULT_PATHS = {
    'problem2': r'D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem2\results\enum_20260523_152013',
    'problem3': r'D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem3\results\3_20260523_144823'
}

NEW_RESULT_PATHS = {
    'problem2': r'D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem2\results',
    'problem3': r'D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem3\results'
}

OUTPUT_DIR = r'D:\PyCharm 2025.2.3\PROJECTS\PythonProject\rest_home\problem4\results'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def read_problem2_results(path):
    result = {}
    
    main_file = os.path.join(path, 'enumerate_result.txt')
    if os.path.exists(main_file):
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            for line in content.split('\n'):
                if '配置字符串:' in line:
                    result['config'] = line.split(':')[1].strip()
                elif '总建设成本:' in line:
                    result['cost'] = float(line.split(':')[1].strip().replace('万元', ''))
                elif '覆盖率:' in line:
                    result['coverage'] = float(line.split(':')[1].strip().replace('%', '')) / 100
                elif '平均满意度:' in line:
                    result['satisfaction'] = float(line.split(':')[1].strip())
                elif '加权得分:' in line:
                    result['score'] = float(line.split(':')[1].strip())
    
    detail_file = os.path.join(path, 'enumerate_full_result.txt')
    if os.path.exists(detail_file):
        with open(detail_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            profit_start = False
            result['stations'] = []
            for i, line in enumerate(lines):
                if '【一、服务站年度利润分析】' in line:
                    profit_start = True
                    continue
                if '【' in line and '服务站年度利润分析' not in line:
                    profit_start = False
                    continue
                if profit_start and line.startswith('-'):
                    continue
                if profit_start and len(line.strip()) > 0 and not line.startswith('【'):
                    if '年收入' in line or '年支出' in line or '年利润' in line:
                        continue
                    parts = line.split()
                    if len(parts) >= 5:
                        result['stations'].append({
                            'name': parts[0],
                            'type': parts[1],
                            'revenue': float(parts[2].replace(',', '')),
                            'expense': float(parts[3].replace(',', '')),
                            'profit': float(parts[4].replace(',', ''))
                        })
            
            if result['stations']:
                result['total_profit'] = sum(s['profit'] for s in result['stations'])
                result['total_revenue'] = sum(s['revenue'] for s in result['stations'])
                result['total_expense'] = sum(s['expense'] for s in result['stations'])
    
    return result


def read_problem3_results(path):
    result = {}
    
    result_files = [f for f in os.listdir(path) if f.endswith('.txt')]
    if result_files:
        result_file = os.path.join(path, result_files[0])
        with open(result_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line in lines:
                if '服务定价:' in line:
                    result['prices'] = json.loads(line.split(':', 1)[1].strip())
                elif '政府补贴总额:' in line:
                    result['subsidy_total'] = float(line.split(':')[1].strip().replace('元', '').replace(',', ''))
                elif '平均满意度:' in line:
                    result['satisfaction'] = float(line.split(':')[1].strip())
                elif '覆盖率:' in line:
                    result['coverage'] = float(line.split(':')[1].strip().replace('%', '')) / 100
                elif '利润率:' in line:
                    result['profit_margin'] = float(line.split(':')[1].strip().replace('%', '')) / 100
    else:
        xlsx_files = [f for f in os.listdir(path) if f.endswith('.xlsx')]
        if xlsx_files:
            xlsx_file = os.path.join(path, xlsx_files[0])
            try:
                all_sheets = pd.read_excel(xlsx_file, sheet_name=None)
                for sheet_name, df in all_sheets.items():
                    if len(df) == 0 or len(df.columns) < 3:
                        continue
                    first_val = str(df.iloc[0, 0]) if len(df) > 0 else ''
                    if '目标函数' in first_val or '决策变量' in first_val or '约束' in first_val:
                        continue

                    if 'satisfaction' not in result:
                        try:
                            col2_vals = pd.to_numeric(df.iloc[:, 2], errors='coerce')
                            valid_vals = col2_vals.dropna()
                            if len(valid_vals) > 0:
                                satisfaction = valid_vals.mean()
                                if 0 < satisfaction < 1:
                                    result['satisfaction'] = float(satisfaction)
                        except:
                            pass

                    if 'subsidy_total' not in result:
                        try:
                            if len(df.columns) >= 4:
                                col_vals = pd.to_numeric(df.iloc[:, 3], errors='coerce')
                                valid_vals = col_vals.dropna()
                                if len(valid_vals) > 0 and valid_vals.iloc[0] > 1000:
                                    result['subsidy_total'] = float(valid_vals.sum())
                                    continue
                        except:
                            pass

                    if 'profit_margin' not in result:
                        try:
                            if len(df.columns) >= 5:
                                for col_idx in [4, 5]:
                                    col_vals = pd.to_numeric(df.iloc[:, col_idx], errors='coerce')
                                    valid_vals = col_vals.dropna()
                                    if len(valid_vals) > 0 and 0 < valid_vals.iloc[0] < 50:
                                        result['profit_margin'] = float(valid_vals.iloc[0]) / 100
                                        break
                        except:
                            pass

                    if 'coverage' not in result:
                        try:
                            for col_idx in range(len(df.columns)):
                                col_vals = pd.to_numeric(df.iloc[:, col_idx], errors='coerce')
                                valid_vals = col_vals.dropna()
                                if len(valid_vals) > 0 and 50 < valid_vals.iloc[0] < 100:
                                    result['coverage'] = float(valid_vals.iloc[0]) / 100
                                    break
                        except:
                            pass

            except Exception as e:
                pass
    
    return result


def get_latest_result_dir(base_path, prefix=''):
    dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d)) and d.startswith(prefix)]
    if not dirs:
        return None
    dirs.sort(reverse=True)
    return os.path.join(base_path, dirs[0])


def analyze_problem2_changes(old_result, new_result):
    analysis = {
        'config_change': old_result.get('config', '') != new_result.get('config', ''),
        'metrics': []
    }
    
    metrics = [
        ('覆盖率', 'coverage', '%'),
        ('满意度', 'satisfaction', ''),
        ('加权得分', 'score', ''),
        ('建设成本', 'cost', '万元'),
        ('总利润', 'total_profit', '元'),
        ('总收入', 'total_revenue', '元'),
        ('总支出', 'total_expense', '元')
    ]
    
    for name, key, unit in metrics:
        old_val = old_result.get(key, 0)
        new_val = new_result.get(key, 0)
        
        if unit == '%':
            old_val = old_val * 100
            new_val = new_val * 100
        
        change = new_val - old_val
        change_pct = (change / old_val * 100) if old_val != 0 else 0
        
        analysis['metrics'].append({
            '指标': name,
            '原值': round(old_val, 2),
            '新值': round(new_val, 2),
            '单位': unit,
            '变化量': round(change, 2),
            '变化率': round(change_pct, 2)
        })
    
    old_stations = old_result.get('stations', [])
    new_stations = new_result.get('stations', [])
    
    analysis['old_station_count'] = len(old_stations)
    analysis['new_station_count'] = len(new_stations)
    analysis['station_names_old'] = [s['name'] for s in old_stations]
    analysis['station_names_new'] = [s['name'] for s in new_stations]
    analysis['station_types_old'] = [f"{s['name']}({s['type']})" for s in old_stations]
    analysis['station_types_new'] = [f"{s['name']}({s['type']})" for s in new_stations]
    
    return analysis


def analyze_problem3_changes(old_result, new_result):
    analysis = {
        'metrics': []
    }
    
    metrics = [
        ('覆盖率', 'coverage', '%'),
        ('满意度', 'satisfaction', ''),
        ('政府补贴总额', 'subsidy_total', '元'),
        ('利润率', 'profit_margin', '%')
    ]
    
    for name, key, unit in metrics:
        old_val = old_result.get(key, 0)
        new_val = new_result.get(key, 0)
        
        if unit == '%':
            old_val = old_val * 100
            new_val = new_val * 100
        
        change = new_val - old_val
        change_pct = (change / old_val * 100) if old_val != 0 else 0
        
        analysis['metrics'].append({
            '指标': name,
            '原值': round(old_val, 2),
            '新值': round(new_val, 2),
            '单位': unit,
            '变化量': round(change, 2),
            '变化率': round(change_pct, 2)
        })
    
    old_prices = old_result.get('prices', {})
    new_prices = new_result.get('prices', {})
    
    analysis['price_changes'] = []
    for service in ['助餐', '日间照料', '上门护理', '康复理疗', '助浴']:
        old_p = old_prices.get(service, 0)
        new_p = new_prices.get(service, 0)
        change = new_p - old_p
        change_pct = (change / old_p * 100) if old_p != 0 else 0
        
        analysis['price_changes'].append({
            '服务': service,
            '原价': old_p,
            '新价': new_p,
            '变化量': change,
            '变化率': round(change_pct, 2)
        })
    
    return analysis


def generate_report(p2_analysis, p3_analysis, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("                    灵敏度分析报告\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("【参数调整说明】\n")
        f.write("-" * 80 + "\n")
        f.write("  1. 老人增长率：年增长率调整为 8%\n")
        f.write("  2. 转移概率：自理→半失能 5.5%，半失能→失能 9.5%\n")
        f.write("  3. 成本变化：日固定管理成本增加 20%\n")
        f.write("  4. 预算调整：总建设预算调整为 140 万元\n")
        f.write("\n")
        
        f.write("【一、问题2：服务站选址与规模优化】\n")
        f.write("-" * 80 + "\n")
        
        f.write("1.1 站点配置变化\n")
        f.write(f"   原配置: {p2_analysis.get('station_types_old', [])}\n")
        f.write(f"   新配置: {p2_analysis.get('station_types_new', [])}\n")
        f.write(f"   站点数量变化: {p2_analysis.get('old_station_count', 0)} → {p2_analysis.get('new_station_count', 0)}\n")
        f.write("\n")
        
        f.write("1.2 关键指标变化\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'指标':<12} {'原值':<12} {'新值':<12} {'变化量':<12} {'变化率':<10}\n")
        f.write("-" * 80 + "\n")
        for m in p2_analysis.get('metrics', []):
            f.write(f"{m['指标']:<12} {str(m['原值'])+m['单位']:<12} {str(m['新值'])+m['单位']:<12} "
                    f"{('+' if m['变化量']>0 else '')+str(m['变化量']):<12} "
                    f"{('+' if m['变化率']>0 else '')+str(m['变化率'])+'%':<10}\n")
        f.write("\n")
        
        f.write("【二、问题3：服务定价与政府补贴优化】\n")
        f.write("-" * 80 + "\n")
        
        f.write("2.1 关键指标变化\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'指标':<12} {'原值':<12} {'新值':<12} {'变化量':<12} {'变化率':<10}\n")
        f.write("-" * 80 + "\n")
        for m in p3_analysis.get('metrics', []):
            if m['单位'] == '元':
                old_str = f"{m['原值']:,.0f}"
                new_str = f"{m['新值']:,.0f}"
                change_str = f"{('+' if m['变化量']>0 else '')}{m['变化量']:,.0f}"
            else:
                old_str = str(m['原值'])
                new_str = str(m['新值'])
                change_str = str(m['变化量'])
            
            f.write(f"{m['指标']:<12} {old_str+m['单位']:<12} {new_str+m['单位']:<12} "
                    f"{change_str:<12} "
                    f"{('+' if m['变化率']>0 else '')+str(m['变化率'])+'%':<10}\n")
        f.write("\n")
        
        f.write("2.2 服务定价变化\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'服务':<12} {'原价(元)':<12} {'新价(元)':<12} {'变化量':<12} {'变化率':<10}\n")
        f.write("-" * 80 + "\n")
        for p in p3_analysis.get('price_changes', []):
            f.write(f"{p['服务']:<12} {p['原价']:<12} {p['新价']:<12} "
                    f"{('+' if p['变化量']>0 else '')+str(p['变化量']):<12} "
                    f"{('+' if p['变化率']>0 else '')+str(p['变化率'])+'%':<10}\n")
        f.write("\n")
        
        f.write("【三、敏感性分析】\n")
        f.write("-" * 80 + "\n")
        f.write("3.1 参数敏感性评估\n")
        f.write("-" * 80 + "\n")
        
        p2_metrics = {m['指标']: m['变化率'] for m in p2_analysis.get('metrics', [])}
        p3_metrics = {m['指标']: m['变化率'] for m in p3_analysis.get('metrics', [])}
        
        f.write("   问题2敏感性:\n")
        f.write(f"     - 覆盖率变化率: {p2_metrics.get('覆盖率', 0):.2f}%\n")
        f.write(f"     - 满意度变化率: {p2_metrics.get('满意度', 0):.2f}%\n")
        f.write(f"     - 总利润变化率: {p2_metrics.get('总利润', 0):.2f}%\n")
        f.write("\n")
        
        f.write("   问题3敏感性:\n")
        f.write(f"     - 覆盖率变化率: {p3_metrics.get('覆盖率', 0):.2f}%\n")
        f.write(f"     - 满意度变化率: {p3_metrics.get('满意度', 0):.2f}%\n")
        f.write(f"     - 补贴总额变化率: {p3_metrics.get('政府补贴总额', 0):.2f}%\n")
        f.write("\n")
        
        f.write("3.2 模型鲁棒性评价\n")
        f.write("-" * 80 + "\n")
        
        sensitivity_scores = []
        for metric, change in {**p2_metrics, **p3_metrics}.items():
            sensitivity_scores.append(abs(change))
        
        avg_sensitivity = sum(sensitivity_scores) / len(sensitivity_scores) if sensitivity_scores else 0
        
        if avg_sensitivity < 10:
            robustness = "高"
            reason = "各项指标变化率均较小，模型对参数变化不敏感"
        elif avg_sensitivity < 20:
            robustness = "中"
            reason = "部分指标有一定变化，但整体仍在可控范围内"
        else:
            robustness = "低"
            reason = "多项指标变化较大，模型对参数变化较为敏感"
        
        f.write(f"   综合鲁棒性等级: {robustness}\n")
        f.write(f"   评价依据: {reason}\n")
        f.write(f"   平均敏感度: {avg_sensitivity:.2f}%\n")
        f.write("\n")
        
        f.write("【四、不确定因素与应对策略】\n")
        f.write("-" * 80 + "\n")
        
        uncertainties = [
            {
                '因素': '实际需求波动',
                '描述': '预测需求与实际需求可能存在偏差',
                '影响': '可能导致服务站容量过剩或不足',
                '策略': '建立需求监测机制，预留10-15%的容量缓冲'
            },
            {
                '因素': '政策变化',
                '描述': '政府补贴政策、医保报销比例可能调整',
                '影响': '直接影响服务定价和运营成本',
                '策略': '设计灵活的定价和补贴模型，支持多场景模拟'
            },
            {
                '因素': '运营效率',
                '描述': '实际运营成本可能高于预期',
                '影响': '压缩利润空间，影响服务质量',
                '策略': '建立成本监控体系，定期评估运营效率'
            },
            {
                '因素': '人口结构变化',
                '描述': '老龄化速度、失能率等可能偏离预测',
                '影响': '需求结构发生变化',
                '策略': '定期更新人口预测模型，动态调整服务配置'
            },
            {
                '因素': '竞争环境变化',
                '描述': '周边地区可能新增养老服务机构',
                '影响': '分流部分客源',
                '策略': '加强服务差异化，提升竞争力'
            }
        ]
        
        for i, item in enumerate(uncertainties, 1):
            f.write(f"   {i}. {item['因素']}\n")
            f.write(f"      - 描述: {item['描述']}\n")
            f.write(f"      - 影响: {item['影响']}\n")
            f.write(f"      - 应对策略: {item['策略']}\n")
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("                    报告结束\n")
        f.write("=" * 80 + "\n")


def main():
    print("=" * 80)
    print("            问题4：灵敏度分析")
    print("=" * 80)
    
    print("\n1. 读取旧参数结果...")
    old_p2 = read_problem2_results(OLD_RESULT_PATHS['problem2'])
    old_p3 = read_problem3_results(OLD_RESULT_PATHS['problem3'])
    
    print(f"   问题2旧结果: {'成功' if old_p2 else '失败'}")
    print(f"   问题3旧结果: {'成功' if old_p3 else '失败'}")
    
    print("\n2. 获取新参数结果路径...")
    new_p2_path = get_latest_result_dir(NEW_RESULT_PATHS['problem2'], 'enum_')
    new_p3_path = get_latest_result_dir(NEW_RESULT_PATHS['problem3'], '')
    
    if not new_p2_path:
        print("   未找到问题2的新结果，请先运行问题2的枚举算法")
        print("   提示: 运行 python problem2/main_enum.py")
        return
    
    if not new_p3_path:
        print("   未找到问题3的新结果，请先运行问题3")
        print("   提示: 运行 python problem3/main.py")
        return
    
    print(f"   问题2新结果路径: {new_p2_path}")
    print(f"   问题3新结果路径: {new_p3_path}")
    
    print("\n3. 读取新参数结果...")
    new_p2 = read_problem2_results(new_p2_path)
    new_p3 = read_problem3_results(new_p3_path)
    
    print(f"   问题2新结果: {'成功' if new_p2 else '失败'}")
    print(f"   问题3新结果: {'成功' if new_p3 else '失败'}")
    
    print("\n4. 分析参数变化影响...")
    p2_analysis = analyze_problem2_changes(old_p2, new_p2)
    p3_analysis = analyze_problem3_changes(old_p3, new_p3)
    
    print("\n5. 生成分析报告...")
    report_path = os.path.join(OUTPUT_DIR, 'sensitivity_analysis_report.txt')
    generate_report(p2_analysis, p3_analysis, report_path)
    
    print(f"\n[OK] 灵敏度分析报告已生成: {report_path}")
    
    print("\n【简要对比】")
    print("-" * 60)
    
    print("\n问题2:")
    for m in p2_analysis.get('metrics', []):
        if m['指标'] in ['覆盖率', '满意度', '加权得分', '总利润']:
            print(f"  {m['指标']}: {m['原值']}{m['单位']} → {m['新值']}{m['单位']} "
                  f"({('+' if m['变化率']>0 else '')}{m['变化率']}%)")
    
    print("\n问题3:")
    for m in p3_analysis.get('metrics', []):
        print(f"  {m['指标']}: {m['原值']}{m['单位']} → {m['新值']}{m['单位']} "
              f"({('+' if m['变化率']>0 else '')}{m['变化率']}%)")


if __name__ == "__main__":
    main()
