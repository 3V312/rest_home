[README.md](https://github.com/user-attachments/files/28695321/README.md)
# rest_home

嵌入式社区养老服务站规划、定价与补贴优化项目。代码按题目拆分为 `problem1` 至 `problem4` 四个模块，围绕社区老年人口预测、服务需求估计、服务站选址与规模优化、服务定价、政府补贴和参数灵敏度分析展开。

## 项目结构

```text
rest_home/
├── shared_config.py      # 共享配置模块（小区列表、距离矩阵、满意度函数等）
├── requirements.txt      # 项目依赖清单
├── problem1/
│   ├── config1.py        # 基础人口、转移概率、服务频次、价格等参数
│   ├── main.py           # 问题1：人口预测、理论需求、实际需求测算
│   ├── main_1.3.py       # 问题1扩展版本
│   ├── drawer.py         # 问题1结果可视化
│   └── draw_dif.py       # 预留文件
├── problem2/
│   ├── config2.py        # 服务站选址、容量、预算等参数（继承共享配置）
│   ├── main_enum.py      # 问题2：枚举法求解服务站选址与规模
│   ├── main_ga.py        # 问题2：遗传算法求解与枚举法对比
│   └── drawer.py         # 预留文件
├── problem3/
│   ├── config3.py        # 定价、补贴、服务站覆盖等参数（继承共享配置）
│   ├── main.py           # 问题3：服务定价、补贴与可及性分析
│   └── drawer.py         # 问题3可及性图表
└── problem4/
    ├── main.py           # 问题4：参数变化灵敏度分析
    └── data/             # 对比结果数据
```

## 环境依赖

建议使用 Python 3.10 及以上版本。使用 `requirements.txt` 安装依赖：

```bash
pip install -r requirements.txt
```

说明：

- `numpy`、`scipy`：数值计算与优化求解。
- `pandas`、`openpyxl`、`xlrd`：Excel 结果读写。
- `matplotlib`、`seaborn`：图表生成。
- 若中文图表显示异常，请安装或配置 `SimHei`、`Microsoft YaHei` 等中文字体。

## 运行方式

在项目根目录执行对应脚本：

```bash
python problem1/main.py
python problem2/main_enum.py
python problem2/main_ga.py
python problem3/main.py
python problem4/main.py
```

推荐运行顺序：

1. 运行 `problem1/main.py`，得到第 5 年末人口预测和服务需求。
2. 运行 `problem2/main_enum.py`，用枚举法确定服务站选址与规模。
3. 运行 `problem2/main_ga.py`，用遗传算法搜索服务站配置，并与枚举结果对比。
4. 运行 `problem3/main.py`，在服务站配置基础上优化服务定价、补贴与可及性。
5. 运行 `problem4/main.py`，对新旧参数结果进行灵敏度分析。

## 各模块说明

### 问题1：人口预测与服务需求测算

入口文件：`problem1/main.py`

主要功能：

- 按自理、半失能、失能三类老人进行 5 年状态转移预测。
- 根据服务频次和服务单价计算各小区理论服务需求。
- 结合收入和消费上限比例，估计实际可支付需求。
- 将结果导出为 Excel 文件。

相关配置：

- `C_DATA`：A-J 小区基础人口、老人结构和收入。
- `P_12`、`P_23`、`DIE_R`、`NEW_R`：状态转移、死亡和新增比例。
- `F_S`、`F_H`、`F_D`：不同老人类型的服务频次。
- `PRICES`、`LIMITS`：服务价格和消费上限。

### 问题2：服务站选址与规模优化

入口文件：

- `problem2/main_enum.py`：枚举法。
- `problem2/main_ga.py`：遗传算法。

主要功能：

- 在 A-J 十个小区中选择服务站建设位置。
- 服务站规模用 `0/1/2/3` 表示：不建站、小型、中型、大型。
- 在预算、服务半径、容量和满意度约束下寻找最优配置。
- 目标综合考虑覆盖率与平均满意度。
- 输出帕累托前沿图、覆盖地图、详细结果文本和最优配置 JSON。

相关配置：

- `DIST_MATRIX`：小区间距离矩阵。
- `CONSTRUCTION_COST`：不同规模服务站建设成本。
- `MAX_CAPACITY`：不同规模服务站日服务能力。
- `BUDGET_MAX`：总建设预算。
- `SERVICE_RADIUS`：服务半径。
- `calc_s1`、`calc_s2`、`calc_s3`：距离、响应、价格满意度函数。

### 问题3：定价、补贴与可及性分析

入口文件：`problem3/main.py`

主要功能：

- 针对已建服务站分别求解有补贴、无补贴两种场景下的最优服务价格。
- 采用 `scipy.optimize.minimize` 的 `trust-constr` 方法处理非线性约束。
- 约束包括利润率区间、补贴上限、服务站容量等。
- 计算服务站收入、成本、利润、利用率、满意度和经济可及性。
- 导出 Excel 结果并生成多张分析图。

相关配置：

- `STATIONS`：服务站位置、规模、容量和覆盖小区。
- `BASE_PRICE`、`REVENUE`：基础成本与收入参数。
- `SUBSIDY_PER_SERVICE`、`DAILY_SUBSIDY_CAP`：补贴规则。
- `PROFIT_MARGIN_MAX`：利润率上限。
- `ELDERLY_BY_TYPE_Y5`、`DEMAND_BY_TYPE_MONTHLY`：第 5 年老人结构与服务需求。

### 问题4：灵敏度分析

入口文件：`problem4/main.py`

主要功能：

- 读取问题2、问题3的新旧结果。
- 对比服务站配置、建设成本、覆盖率、满意度、利润、补贴和定价变化。
- 生成灵敏度分析报告 `sensitivity_analysis_report.txt`。

运行前需要先生成：

- 问题2的新枚举结果目录：`problem2/results/enum_*`
- 问题3的新结果目录：`problem3/results/*`

## 输出文件

常见输出位置如下：

```text
problem1/results/                  # 问题1 Excel 与图表结果
problem2/results/enum_时间戳/       # 枚举法结果
problem2/results/ga_时间戳/         # 遗传算法结果
problem2/results/optimum_config.json
problem3/results/3_时间戳/          # 定价、补贴、可及性 Excel 与图表
problem4/results/                  # 灵敏度分析报告
```

## 注意事项

- 所有文件均使用 UTF-8 编码，中文注释和字符串显示正常。
- `problem1/drawer.py` 默认读取指定历史 Excel 文件，运行前需要先确认 `file_path` 指向已存在的结果文件。
- `problem2/main_ga.py` 会尝试读取指定枚举结果目录用于对比；若不存在，会使用默认参考得分继续运行。
- `problem4/main.py` 依赖问题2、问题3已存在的新旧结果，首次运行前需要检查 `OLD_RESULT_PATHS` 和 `NEW_RESULT_PATHS`。
- `.venv` 和 `.idea` 属于本地环境与 IDE 配置，通常不需要纳入论文或建模说明。


