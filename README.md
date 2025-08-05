# MySQL量化交易策略研究

一个专注于量化交易策略回测和参数优化的研究项目，基于MySQL数据库进行股票数据分析和策略验证。

## 项目特色

- 📊 **量化回测** - 完整的策略回测框架
- 🔧 **参数优化** - 多种优化算法支持
- 📈 **技术指标** - 丰富的技术分析指标
- 🎯 **策略验证** - 严格的回测验证流程
- 📋 **结果分析** - 详细的回测结果分析

## 核心功能

### 策略回测 (`backtest.py`)
- 支持多种交易策略
- 完整的回测流程
- 详细的交易记录
- 性能指标计算

### 参数优化 (`param_optimizer.py`)
- 网格搜索优化
- 贝叶斯优化
- 遗传算法优化
- 多进程并行计算

### 数据库工具 (`db_utils.py`)
- MySQL数据库连接
- 数据查询和写入
- 批量数据处理

## 项目结构

```
MYSQL-策略研究/
├── backtest.py                 # 策略回测脚本
├── param_optimizer.py          # 参数优化脚本
├── config.py                   # 配置文件
├── db_utils.py                 # 数据库工具
├── logging_config.py           # 日志配置
├── requirements.txt            # 依赖包列表
├── README.md                   # 项目说明
├── turnover_rate_ratio_5_指标说明.md  # 指标说明文档
├── 筹码数据应用原理及组合应用指南.md   # 策略指南
├── micro_cap_backtest/         # 小市值回测
├── optimization_results/       # 优化结果
├── output/                     # 输出目录
└── test/                       # 测试目录
```

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置数据库
编辑 `config.py` 文件，配置MySQL数据库连接信息：
```python
MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'your_username'
MYSQL_PASSWORD = 'your_password'
MYSQL_DB = 'stock_data'
```

### 3. 运行回测
```bash
python backtest.py
```

### 4. 参数优化
```bash
python param_optimizer.py
```

## 配置说明

### 策略参数配置
在 `backtest.py` 中的 `StrategyConfig` 类中配置策略参数：
- 初始资金
- 最小持仓天数
- 买入条件
- 卖出条件
- 技术指标参数

### 优化参数配置
在 `param_optimizer.py` 中配置优化参数：
- 参数搜索范围
- 优化算法选择
- 并行计算设置
- 结果保存路径

## 使用示例

### 基本回测
```python
from backtest import backtest_strategy, StrategyConfig

# 创建策略配置
config = StrategyConfig({
    'INITIAL_AMOUNT': 100000,
    'MIN_HOLD_DAYS': 2,
    'VSHAPE_PREV_PRICE_POSITION': 0.17
})

# 运行回测
result = backtest_strategy(stock_data, '000001', config)
```

### 参数优化
```python
from param_optimizer import ParameterOptimizer

# 创建优化器
optimizer = ParameterOptimizer(
    stock_files=['stock1.csv', 'stock2.csv'],
    method='bayesian',
    n_jobs=4
)

# 运行优化
best_params = optimizer.optimize()
```

## 结果分析

### 回测结果
- 总收益率
- 年化收益率
- 最大回撤
- 夏普比率
- 胜率统计

### 优化结果
- 最佳参数组合
- 参数敏感性分析
- 优化过程记录
- 结果可视化

## 注意事项

1. **数据质量** - 确保股票数据完整性和准确性
2. **参数设置** - 根据实际情况调整策略参数
3. **风险控制** - 注意回测结果的过拟合风险
4. **性能优化** - 大数据量时考虑使用并行计算

## 版本控制

本项目使用Git进行版本控制，代码已推送到GitHub：
https://github.com/hgy2008v/mysql-strategy-research

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 联系方式

如有问题或建议，请通过GitHub Issues联系。 