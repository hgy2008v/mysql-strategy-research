# 股票数据处理系统完整说明文档

## 项目概述

本系统是一个完整的股票数据处理平台，用于自动化下载、处理A股股票及相关市场数据，并批量计算多种技术指标。系统支持全量处理和增量处理两种模式，适合量化选股、策略开发等场景。

### 主要功能
- **数据下载**: 自动下载股票日线数据和其他市场数据
- **数据处理**: 支持全量和增量两种处理模式
- **技术指标**: 计算多种技术指标（布林带、MACD、KDJ、RSI等）
- **状态监控**: 实时监控处理进度和数据质量
- **性能优化**: 支持并行处理、批量写入、内存优化

## 系统架构

### 核心文件结构
```
├── main.py                          # 主入口脚本
├── stock_data_processor.py          # 主处理脚本（全量+增量）
├── process_incremental.py           # 专用增量处理脚本
├── check_processing_status.py       # 状态监控脚本
├── download_stock_daily_incremental.py  # 股票数据下载
├── download_other_data.py          # 其他市场数据下载
├── config.py                       # 配置文件
├── db_utils.py                     # 数据库工具
└── logging_config.py               # 日志配置
```

### 数据库表结构
- `stock_daily`: 原始股票数据表
- `stock_daily_processed`: 处理后的股票数据表（包含技术指标）

## 使用方法

### 1. 主入口脚本（推荐）

#### 默认增量处理
```bash
python main.py
```

#### 全量处理
```bash
python main.py --mode full
```

#### 增量处理（指定天数）
```bash
python main.py --mode incremental --days-back 60
```

#### 仅下载数据
```bash
python main.py --download-only
```

#### 跳过其他市场数据
```bash
python main.py --skip-other-data
```

#### 日志控制
```bash
python main.py --log-level quiet
python main.py --log-file logs/process.log
```

### 2. 专用脚本

#### 查看处理状态
```bash
python check_processing_status.py
python check_processing_status.py 60  # 指定天数
```

#### 增量处理
```bash
python process_incremental.py
python process_incremental.py 60     # 指定天数
python process_incremental.py 200 500  # 指定天数和批处理大小
```

#### 全量处理
```bash
python stock_data_processor.py
```

### 3. 命令行参数说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `--mode` | 处理模式：full/incremental | `--mode full` |
| `--days-back` | 增量处理向前查找天数 | `--days-back 60` |
| `--log-level` | 日志级别：quiet/normal/verbose | `--log-level quiet` |
| `--log-file` | 日志文件路径 | `--log-file logs/process.log` |
| `--download-only` | 仅执行数据下载 | `--download-only` |
| `--skip-other-data` | 跳过其他市场数据下载 | `--skip-other-data` |

## 增量处理系统

### 系统特点
- **自动识别**: 自动识别需要处理的新增数据
- **历史数据**: 获取足够的历史数据确保技术指标计算准确性
- **批量处理**: 支持批量处理多个股票，并行处理提高效率
- **状态监控**: 实时监控处理进度，提供详细的统计信息

### 参数设计
- **INCREMENTAL_DAYS_BACK**: 增量识别向前查找天数，默认200天
- **HISTORY_DAYS**: 历史数据获取天数，默认756天
- **LONG_TERM_WINDOW**: 长期窗口，默认756天

### 参数关系
```
HISTORY_DAYS (756天) >= LONG_TERM_WINDOW (756天) >= INCREMENTAL_DAYS_BACK (200天)
```

### 使用场景
- **日常增量**: `INCREMENTAL_DAYS_BACK = 7-30` 天
- **定期增量**: `INCREMENTAL_DAYS_BACK = 30-60` 天
- **全量更新**: 使用全量处理脚本

## 技术指标说明

### 1. 布林带相关指标

#### 基础指标
- **MA (移动平均线)**: 20日移动平均线，反映股价的中期趋势
- **STD (标准差)**: 20日价格波动的标准差，衡量股价的波动性
- **RSD (相对标准差)**: 标准差相对于移动平均线的百分比
- **Upper_Band (上轨)**: 布林带上轨，通常作为阻力位
- **Lower_Band (下轨)**: 布林带下轨，通常作为支撑位

#### 价格位置指标
- **Band_price_position**: 当前价格在布林带内的相对位置 (0-1)
- **90d_price_position**: 当前价格在90日价格区间内的相对位置
- **3year_price_position**: 当前价格在3年价格区间内的相对位置

### 2. 价格相对指标

#### 价格相对低点
- **price_to_low**: 当前价格相对于90日最低价的倍数
- **3year_price_to_low**: 当前价格相对于3年最低价的倍数
- **3year_price_to_high**: 当前价格相对于3年最高价的倍数

### 3. PE估值指标

- **3year_pe_position**: 当前PE在3年PE区间内的相对位置
- **is_loss**: 标识股票是否处于亏损状态

### 4. 价格转折信号

- **price_position_cross**: 价格转折信号 (1:底部转折, -1:顶部转折, 0:无转折)
- **reversal_ratio**: 价格转折的幅度大小

### 5. 趋势指标

- **MA_slope**: MA趋势斜率
- **CLOSE_slope**: CLOSE趋势斜率

### 6. 技术指标

- **MACD**: MACD指标及其相关信号
- **KDJ**: KDJ指标及其交叉信号
- **RSI**: RSI相对强弱指标
- **BBI**: 多空均线指标

### 7. 连续指标

- **成交量连续增加天数**: 成交量连续增加的天数
- **主力净量连续大于0天数**: 主力净量连续为正的天数
- **股价连续下跌天数**: 股价连续下跌的天数
- **连板天数**: 连续涨停的天数

## 指标组合使用策略

### 1. 超买超卖判断
```
超买条件: Band_price_position > 0.8 且 90d_price_position > 0.8
超卖条件: Band_price_position < 0.2 且 90d_price_position < 0.2
```

### 2. 投资价值评估
```
低估条件: 
- 3year_price_position < 0.3
- price_to_low < 1.3
- 3year_pe_position < 0.3 (非亏损股)

高估条件:
- 3year_price_position > 0.8
- price_to_low > 2.0
- 3year_pe_position > 0.8 (非亏损股)
```

### 3. 趋势判断
```
上升趋势: 
- MA_slope > 0
- CLOSE_slope > 0
- price_position_cross = 1

下降趋势:
- MA_slope < 0
- CLOSE_slope < 0
- price_position_cross = -1
```

### 4. 风险控制
```
高风险信号:
- RSD > 30 (高波动)
- reversal_ratio > 0.05 (大幅转折)
- 3year_price_to_high > 0.9 (接近历史高点)

低风险信号:
- RSD < 15 (低波动)
- reversal_ratio < 0.02 (小幅转折)
- price_to_low < 1.2 (接近低点)
```

## 性能优化

### 1. 内存优化
- 分批处理避免内存溢出
- 及时释放不需要的数据
- 强制垃圾回收

### 2. 数据库优化
- 使用REPLACE INTO避免重复数据
- 批量写入减少数据库压力
- 适当的批次大小

### 3. 并行处理
- 多线程并行处理股票数据
- 可配置并行度
- 超时控制

## 错误处理

### 1. 数据异常
- 自动跳过无效数据
- 记录错误日志
- 继续处理其他数据

### 2. 数据库异常
- 重试机制
- 连接超时处理
- 事务回滚

### 3. 内存异常
- 内存监控
- 强制垃圾回收
- 分批处理

## 日志管理

### 日志文件
- `incremental_process.log`: 增量处理日志
- `status_check.log`: 状态检查日志
- `process_stock_data.log`: 主处理日志

### 日志级别
- INFO: 一般信息
- WARNING: 警告信息
- ERROR: 错误信息

## 注意事项

### 1. 数据一致性
- 确保原始数据表 `stock_daily` 的数据完整性
- 定期备份重要数据
- 监控数据质量

### 2. 性能考虑
- 根据服务器配置调整并行度
- 监控内存使用情况
- 避免在业务高峰期运行

### 3. 错误恢复
- 保存失败批次到 `FAIL_BATCH_DIR`
- 支持断点续传
- 提供重试机制

### 4. 参数调优
- `INCREMENTAL_DAYS_BACK` 建议设置为 `LONG_TERM_WINDOW` 的 1/4 到 1/2
- `HISTORY_DAYS` 必须大于等于 `LONG_TERM_WINDOW`
- 根据数据更新频率调整增量识别天数

## 常见问题

### Q: 为什么增量识别默认200天而不是30天？
A: 因为技术指标计算需要756天的历史数据，200天约为756天的1/4，确保有足够的数据进行增量识别，同时避免处理过多不必要的数据。

### Q: 增量处理失败怎么办？
A: 检查日志文件，确认错误原因，可以重新运行增量处理或进行全量处理。

### Q: 如何提高处理速度？
A: 可以增加并行度、减少批次大小、优化数据库配置等。

### Q: 数据质量有问题怎么办？
A: 运行状态检查脚本，根据建议进行相应的处理。

### Q: 如何监控处理进度？
A: 使用状态监控脚本，定期检查处理状态和覆盖率。

### Q: 如何选择合适的增量识别天数？
A: 根据数据更新频率：
- 高频更新（每日）：7-30天
- 中频更新（每周）：30-60天
- 低频更新（每月）：180天

## 技术支持

如有问题，请检查：
1. 数据库连接配置
2. 表结构是否正确
3. 日志文件中的错误信息
4. 系统资源使用情况
5. 参数配置是否合理

## 更新日志

- 2024年：初始版本，包含基础技术指标
- 2024年：增加增量处理功能
- 2024年：完善技术指标体系，优化批量写入性能
- 2024年：重构为模块化设计，支持全量和增量两种模式
- 2024年：优化参数设计，提高处理效率和准确性 