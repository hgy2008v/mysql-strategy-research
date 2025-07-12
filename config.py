import logging

MYSQL_HOST = 'localhost'
MYSQL_PORT = 3306
MYSQL_USER = 'root'
MYSQL_PASSWORD = '1234'
MYSQL_DB = 'stock_data'

class Config:
    """
    配置文件类，用于集中管理所有可配置参数。
    """

    # 日志配置
    LOG_LEVEL = logging.INFO  # 日志级别，默认为 INFO
    LOG_FILE = "process_stock_data.log"  # 日志文件路径，默认为当前目录下的 process_stock_data.log

    # 文件处理配置
    OUTPUT_DIR = "stock_data"  # 输出目录，默认为 stock_data
    REQUIRED_FIELDS = ['trade_date', 'open', 'high', 'low', 'close', 'vol', '主力净量']  # 数据文件中必须包含的字段

    # 技术指标配置
    KDJ_WINDOW = 9  # KDJ 指标的窗口大小，默认为 9
    MACD_SHORT_WINDOW = 5  # MACD 短期均线窗口大小，默认为 12
    MACD_LONG_WINDOW = 34  # MACD 长期均线窗口大小，默认为 26
    MACD_SIGNAL_WINDOW = 5  # MACD 信号线窗口大小，默认为 9
    RSI_PERIOD = 14  # RSI 指标的周期，默认为 14
    BBI_WINDOWS = [3, 6, 12, 24]  # BBI 指标的窗口大小列表，默认为 [3, 6, 12, 24]
    TREND_SHORT_WINDOW = 5  # 短期趋势的窗口大小
    TREND_LONG_WINDOW = 20  # 长期趋势的窗口大小
    BOLLINGER_WINDOW = 20  # 布林带窗口大小，默认为 20
    BOLLINGER_NUM_STD = 2  # 布林带的标准差倍数，默认为 2

    # 横盘判断配置
    SIDEWAYS_WINDOW = 20  # 短期波动范围的窗口大小
    SIDEWAYS_PRICE_THRESHOLD = 0.05  # 短期价格波动范围的阈值（5%）
    SIDEWAYS_MA_THRESHOLD = 0.02  # 短期均线差值阈值，默认为 0.02（2%）
    SIDEWAYS_VOLATILITY_THRESHOLD = 0.01  # 短期波动率阈值，默认为 0.01（1%）
    SIDEWAYS_BOLLINGER_THRESHOLD = 0.05  # 短期布林带宽度阈值，默认为 0.05（5%）

    # 长期横盘判断配置
    LONG_SIDEWAYS_WINDOW = 60  # 长期波动范围的窗口大小
    LONG_SIDEWAYS_PRICE_THRESHOLD = 0.1  # 长期价格波动范围的阈值（10%）
    LONG_SIDEWAYS_MA_THRESHOLD = 0.05  # 长期均线差值阈值，默认为 0.05（5%）
    LONG_SIDEWAYS_VOLATILITY_THRESHOLD = 0.02  # 长期波动率阈值，默认为 0.02（2%）
    LONG_SIDEWAYS_BOLLINGER_THRESHOLD = 0.1  # 长期布林带宽度阈值，默认为 0.1（10%）

    # 阶段性高低位判断配置
    STAGE_HIGH_LOW_WINDOW = 120  # 阶段性高低位判断的窗口大小，默认为 20

    # 其他配置
    VOLUME_SCALE = 100  # 成交量缩放比例，默认为 10000
    DIVERGENCE_THRESHOLD = 0.1  # 分歧判断的阈值，默认为 0.1
    VOLUME_ROLLING_WINDOW = 20  # 成交量滚动均值的窗口大小，默认为 20

    # 阶段性高低位判断参数
    STAGE_LEVEL_CONFIG = {
        'KDJ_HIGH_THRESHOLD': 80,  # KDJ 高位阈值
        'KDJ_LOW_THRESHOLD': 20,   # KDJ 低位阈值
        'RSI_HIGH_THRESHOLD': 70,  # RSI 超买阈值
        'RSI_LOW_THRESHOLD': 30,   # RSI 超卖阈值
        'BOLLINGER_UPPER_THRESHOLD': 0.98,  # 布林带上轨接近阈值
        'BOLLINGER_LOWER_THRESHOLD': 1.02,  # 布林带下轨接近阈值
        'MACD_HISTOGRAM_WINDOW': 20,  # MACD 柱状图均值计算窗口
    }

    # 阶段位置判断阈值
    # STAGE_LEVEL_THRESHOLD = 0.05  # 5% 的阈值范围
    
    # 趋势窗口大小（用于计算MA趋势斜率）
    TREND_WINDOW = 10  # 可以根据需要调整这个值

    MIN_PRICE_WINDOW = 90  # 与 StrategyConfig.MIN_PRICE_WINDOW 保持一致  

    # MySQL数据库配置
    # MYSQL_HOST = 'localhost'
    # MYSQL_PORT = 3306
    # MYSQL_USER = 'root'
    # MYSQL_PASSWORD = '1234'
    # MYSQL_DB = 'stock_data'  