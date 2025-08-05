# 微盘股回测系统

这是一个用于回测微盘股交易策略的Python系统。

## 项目结构

```
micro_cap_backtest/
├── data/               # 数据目录
│   └── bak_daily.csv   # 历史日线数据
├── results/            # 结果目录
│   ├── backtest_results.csv    # 回测结果
│   ├── portfolio_value.csv     # 组合价值历史
│   └── trade_history.csv       # 交易历史记录
├── backtest_micro_caps.py      # 主程序
└── README.md           # 说明文档
```

## 环境要求

- Python 3.7+
- pandas
- numpy
- tushare
- TA-Lib

## 安装依赖

1. 安装 TA-Lib：
   - 访问 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
   - 下载对应您Python版本的whl文件
   - 安装下载的whl文件：
     ```bash
     pip install TA_Lib‑0.4.24‑cp39‑cp39‑win_amd64.whl
     ```

2. 安装其他依赖：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. 确保已安装所有依赖包
2. 在 `backtest_micro_caps.py` 中配置您的 Tushare token
3. 运行回测程序：

```bash
python backtest_micro_caps.py
```

## 配置说明

在 `backtest_micro_caps.py` 中的 `CONFIG` 字典中可以修改以下参数：

- `ts_token`: Tushare API token
- `price_threshold`: 价格阈值（元）
- `top_n`: 排名前N名
- `hold_days`: 持有天数
- `stock_count`: 每次买入的股票数量
- `position_size`: 每只股票的买入金额（元）

## 数据说明

- 数据文件保存在 `data` 目录下
- 回测结果保存在 `results` 目录下
- 程序会自动缓存下载的数据，避免重复下载

## 注意事项

1. 首次运行时会下载历史数据，可能需要一些时间
2. 确保有足够的磁盘空间存储数据文件
3. 注意 Tushare 的 API 调用频率限制
4. TA-Lib 的安装可能需要额外的步骤，请参考安装说明 