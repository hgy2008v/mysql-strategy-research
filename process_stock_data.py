import pandas as pd
import numpy as np
import os
import logging
import time
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial
import db_utils
from sqlalchemy import inspect
import random
from sqlalchemy import text

# 参数配置
class Config:
    # 数据处理参数
    MIN_PRICE_WINDOW = 90  # 最低价计算窗口
    TREND_WINDOW = 10  # 趋势计算窗口
    VOLUME_SCALE = 100  # 成交量缩放因子
    LONG_TERM_WINDOW = 756 # 长期窗口，用于计算3年相关指标
    
    # 技术指标参数
    MACD_SHORT_WINDOW = 12  # MACD短期窗口
    MACD_LONG_WINDOW = 26  # MACD长期窗口
    MACD_SIGNAL_WINDOW = 9  # MACD信号线窗口
    KDJ_WINDOW = 9  # KDJ计算窗口
    RSI_PERIOD = 14  # RSI计算周期
    BBI_WINDOWS = [3, 6, 12, 24]  # BBI移动平均窗口
    
    # 数据质量控制参数
    PRICE_CHANGE_THRESHOLD = 0.1  # 价格变化阈值
    MA_CHANGE_THRESHOLD = 0.2  # MA变化阈值
    VOLUME_CHANGE_THRESHOLD = 2.0  # 成交量变化阈值
    RSD_LIMIT = 50.0  # RSD限制值
    SLOPE_LIMIT = 3.0  # 斜率限制值
    
    # 输入输出配置
    OUTPUT_DIR = 'stock_data'  # 输出目录
    REQUIRED_FIELDS = ['trade_date', 'open', 'high', 'low', 'close', 'vol']  # 必需字段

# 确保Config类中包含MIN_PRICE_WINDOW参数
# 如果在config.py中未定义，可以在此处添加
if not hasattr(Config, 'MIN_PRICE_WINDOW'):
    # 设置为与backtest.py中StrategyConfig.MIN_PRICE_WINDOW相同的值
    Config.MIN_PRICE_WINDOW = 90

# 配置日志
def setup_logging():
    """配置日志输出"""
    handlers = [logging.StreamHandler()]
    if Config.LOG_FILE:
        handlers.append(logging.FileHandler(Config.LOG_FILE, encoding='utf-8'))
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers
    )

def handle_missing_values(df, method='interpolate'):
    """
    处理DataFrame或Series中的缺失值，同时解决数据类型警告
    
    参数:
        df (pd.DataFrame 或 pd.Series): 输入的数据框或序列
        method (str): 处理方法，可选 'interpolate'（插值）, 'ffill'（前向填充）, 'bfill'（后向填充）
    
    返回:
        pd.DataFrame 或 pd.Series: 处理后的数据框或序列
    """
    valid_methods = ['interpolate', 'ffill', 'bfill']
    if method not in valid_methods:
        logging.warning(f"无效的处理方法: {method}，将使用默认方法'interpolate'")
        method = 'interpolate'
    
    # 处理Series类型
    if isinstance(df, pd.Series):
        try:
            if pd.api.types.is_numeric_dtype(df):
                if method == 'interpolate':
                    df = df.interpolate(method='linear')
                elif method == 'ffill':
                    df = df.ffill()
                elif method == 'bfill':
                    df = df.bfill()
            else:
                df = df.ffill().bfill()
        except Exception as e:
            logging.warning(f"处理Series时出错: {str(e)}，将使用前后填充")
            df = df.ffill().bfill()
        
    # 处理DataFrame类型
    else:
        for col in df.columns:
            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    if method == 'interpolate':
                        df[col] = df[col].interpolate(method='linear')
                    elif method == 'ffill':
                        df[col] = df[col].ffill()
                    elif method == 'bfill':
                        df[col] = df[col].bfill()
                else:
                    df[col] = df[col].ffill().bfill()
            except Exception as e:
                logging.warning(f"处理列 {col} 时出错: {str(e)}，将使用前后填充")
                df[col] = df[col].ffill().bfill()
    
    return df

# 技术指标计算函数
def calculate_kdj(df):
    """计算 KDJ 指标"""
    # 确保输入数据的列存在
    if not all(col in df.columns for col in ['low', 'high', 'close']):
        logging.warning("缺少计算KDJ所需的列，跳过KDJ计算")
        return df
    
    # 复制相关列以避免修改原始数据
    temp_df = df[['low', 'high', 'close']].copy()
    
    # 处理输入数据的缺失值
    temp_df = handle_missing_values(temp_df)
    
    low_min = temp_df['low'].rolling(window=Config.KDJ_WINDOW, min_periods=1).min()
    high_max = temp_df['high'].rolling(window=Config.KDJ_WINDOW, min_periods=1).max()
    
    # 处理可能的除零情况
    denominator = high_max - low_min
    denominator = denominator.replace(0, np.nan)
    rsv = (temp_df['close'] - low_min) / denominator * 100
    
    # 使用指数移动平均计算K和D
    K = rsv.ewm(com=2, adjust=False).mean()
    D = K.ewm(com=2, adjust=False).mean()
    
    # 处理可能的缺失值
    K = handle_missing_values(K)
    D = handle_missing_values(D)
    
    kdj_signal = np.select(
        [(K > D) & (K.shift(1) <= D.shift(1)), (K < D) & (K.shift(1) >= D.shift(1))],
        [1, -1],
        default=0
    )
    
    df['K'] = K
    df['D'] = D
    df['KDJ_cross'] = kdj_signal
    return df

def calculate_macd(df):
    """计算 MACD 指标"""
    # 确保输入数据的列存在
    if 'close' not in df.columns:
        logging.warning("缺少计算MACD所需的close列，跳过MACD计算")
        return df
    
    # 复制相关列以避免修改原始数据
    temp_df = df[['close']].copy()
    
    # 处理输入数据的缺失值
    temp_df = handle_missing_values(temp_df)
    
    # 计算短期和长期EMA
    df['EMA_short'] = temp_df['close'].ewm(span=Config.MACD_SHORT_WINDOW, adjust=False).mean()
    df['EMA_long'] = temp_df['close'].ewm(span=Config.MACD_LONG_WINDOW, adjust=False).mean()
    
    # 处理EMA计算中的缺失值
    df['EMA_short'] = handle_missing_values(df['EMA_short'])
    df['EMA_long'] = handle_missing_values(df['EMA_long'])
    
    # 计算MACD线
    df['MACD'] = df['EMA_short'] - df['EMA_long']
    df['MACD'] = handle_missing_values(df['MACD'])
    
    # 计算信号线
    df['Signal'] = df['MACD'].ewm(span=Config.MACD_SIGNAL_WINDOW, adjust=False).mean()
    df['Signal'] = handle_missing_values(df['Signal'])
    
    # 计算MACD柱状图
    df['MACD_Histogram'] = df['MACD'] - df['Signal']
    df['MACD_Histogram'] = handle_missing_values(df['MACD_Histogram'])
    
    # 计算柱状图变化
    df['Histogram_Change'] = df['MACD_Histogram'].diff()
    df['Histogram_Change'] = handle_missing_values(df['Histogram_Change'])
    
    # 判断金叉/死叉
    golden_cross = (df['MACD'] > df['Signal']) & (df['MACD'].shift(1) <= df['Signal'].shift(1))
    dead_cross = (df['MACD'] < df['Signal']) & (df['MACD'].shift(1) >= df['Signal'].shift(1))
    
    # 判断水上/水下
    above_zero = df['MACD'] > 0
    below_zero = df['MACD'] <= 0
    
    # 组合条件
    df['MACD_cross'] = np.select(
        [
            golden_cross & above_zero,  # 水上金叉
            golden_cross & below_zero,  # 水下金叉
            dead_cross & above_zero,    # 水上死叉
            dead_cross & below_zero     # 水下死叉
        ],
        [
            "水上金叉",
            "水下金叉",
            "水上死叉",
            "水下死叉"
        ],
        default=0
    )
    
    return df

def calculate_rsi(df):
    """计算 RSI 指标"""
    # 确保输入数据的列存在
    if 'close' not in df.columns:
        logging.warning("缺少计算RSI所需的close列，跳过RSI计算")
        return df
    
    # 复制相关列以避免修改原始数据
    temp_df = df[['close']].copy()
    
    # 处理输入数据的缺失值
    temp_df = handle_missing_values(temp_df)
    
    # 计算价格变化
    delta = temp_df['close'].diff()
    delta = handle_missing_values(delta)
    
    # 分别计算上涨和下跌
    gain = (delta.where(delta > 0, 0)).rolling(window=Config.RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=Config.RSI_PERIOD).mean()
    
    # 处理可能的除零情况
    loss = loss.replace(0, np.nan)
    rs = gain / loss
    rs = handle_missing_values(rs, method='ffill')
    
    # 计算RSI
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = handle_missing_values(df['RSI'])
    
    return df

def calculate_bbi(df):
    """计算 BBI 指标"""
    # 确保输入数据的列存在
    if 'close' not in df.columns:
        logging.warning("缺少计算BBI所需的close列，跳过BBI计算")
        return df
    
    # 复制相关列以避免修改原始数据
    temp_df = df[['close']].copy()
    
    # 处理输入数据的缺失值
    temp_df = handle_missing_values(temp_df)
    
    # 计算多个移动平均线
    ma_values = []
    for w in Config.BBI_WINDOWS:
        ma = temp_df['close'].rolling(window=w).mean()
        ma = handle_missing_values(ma)
        ma_values.append(ma)
    
    # 计算BBI
    df['BBI'] = sum(ma_values) / len(ma_values)
    df['BBI'] = handle_missing_values(df['BBI'])
    
    return df

def calculate_bollinger_bands(df, ts_code='Unknown'):
    """计算布林带指标"""
    # 确保输入数据的列存在
    if 'close' not in df.columns:
        logging.warning(f"股票 {ts_code} 缺少计算布林带所需的close列，跳过布林带计算")
        return df
    
    # 首先确保基础价格数据没有缺失值
    if df['close'].isnull().any():
        logging.warning(f"股票 {ts_code} 'close'列中存在缺失值，进行前向/后向填充")
        df['close'] = df['close'].ffill().bfill()
    
    # 确保计算窗口足够
    if len(df) < 20:
        logging.warning(f"股票 {ts_code} 数据长度({len(df)})不足20，可能影响MA计算质量")
    
    # 计算中轨（MA）
    df['MA'] = df['close'].rolling(window=20, min_periods=1).mean()
    # 确保MA没有缺失值
    df['MA'] = df['MA'].ffill().bfill()
    
    # 计算标准差
    df['STD'] = df['close'].rolling(window=20, min_periods=1).std()
    # 确保STD没有缺失值
    df['STD'] = df['STD'].ffill().bfill()
    
    # 计算相对标准差，避免除零错误
    df['RSD'] = df.apply(lambda row: 0 if row['MA'] == 0 else (row['STD'] / row['MA']) * 100, axis=1)
    # 确保RSD没有缺失值
    df['RSD'] = df['RSD'].ffill().bfill()

    # 计算RSD变化率
    pre_rsd = df['RSD'].shift(1).replace(0, np.nan)
    df['RSD_chg'] = (df['RSD'] / pre_rsd) - 1
    df['RSD_chg'] = df['RSD_chg'].ffill().bfill().fillna(0)

    # 计算前一天的RSD变化率
    df['prev_RSD'] = df['RSD'].shift(1)
    df['prev_RSD'] = df['prev_RSD'].ffill().bfill()
    
    # 计算布林带上下轨
    df['Upper_Band'] = df['MA'] + (df['STD'] * 2)
    df['Lower_Band'] = df['MA'] - (df['STD'] * 2)
    
    # 确保上下轨没有缺失值
    df['Upper_Band'] = df['Upper_Band'].ffill().bfill()
    df['Lower_Band'] = df['Lower_Band'].ffill().bfill()
    
    # 计算布林带宽度，避免除零错误
    bollinger_width = df['Upper_Band'] - df['Lower_Band']
    
    # 计算价格位置，处理可能的零宽度情况
    df['Band_price_position'] = df.apply(
        lambda row: 0.5 if (row['Upper_Band'] - row['Lower_Band']) == 0 
        else (row['close'] - row['Lower_Band']) / (row['Upper_Band'] - row['Lower_Band']), 
        axis=1
    )
    
    # 确保Band_price_position没有缺失值
    df['Band_price_position'] = df['Band_price_position'].ffill().bfill()
    
    # 保留原始的Band_price_position值，不限制在0-1范围内
    df['prev_Band_price_position'] = df['Band_price_position'].shift(1)
    # 确保prev_Band_price_position没有缺失值
    df['prev_Band_price_position'] = df['prev_Band_price_position'].ffill().bfill()

    # --- 新增：计算90日价格相对位置 ---
    min_price_90d = df['close'].rolling(window=90, min_periods=1).min()
    max_price_90d = df['close'].rolling(window=90, min_periods=1).max()
    price_range_90d = (max_price_90d - min_price_90d).replace(0, np.nan) # 避免除以0
    
    df['90d_price_position'] = (df['close'] - min_price_90d) / price_range_90d
    # 当区间为0时，位置在中间0.5；其他NaN用0填充；最后将结果限制在0-1之间
    df['90d_price_position'] = df['90d_price_position'].fillna(0.5).ffill().bfill().clip(0, 1)
    
    df['prev_90d_price_position'] = df['90d_price_position'].shift(1)
    df['prev_90d_price_position'] = df['prev_90d_price_position'].ffill().bfill().fillna(0)

    # --- 新增：计算3年价格相对位置 ---
    min_price_3y = df['close'].rolling(window=Config.LONG_TERM_WINDOW, min_periods=1).min()
    max_price_3y = df['close'].rolling(window=Config.LONG_TERM_WINDOW, min_periods=1).max()
    price_range_3y = (max_price_3y - min_price_3y).replace(0, np.nan)

    df['3year_price_position'] = (df['close'] - min_price_3y) / price_range_3y
    df['3year_price_position'] = df['3year_price_position'].fillna(0.5).ffill().bfill().clip(0, 1)

    # --- 新增：计算3年PE相对位置 (修正逻辑) ---
    if 'pe' in df.columns and not df['pe'].isnull().all():
        # 1. 明确标记亏损状态 (PE为NaN或小于等于0)
        df['is_loss'] = df['pe'].isnull() | (df['pe'] <= 0)

        # 2. 在正PE中计算历史估值区间
        pe_positive = df['pe'].where(df['pe'] > 0)
        min_pe_3y = pe_positive.rolling(window=Config.LONG_TERM_WINDOW, min_periods=1).min().ffill().bfill()
        max_pe_3y = pe_positive.rolling(window=Config.LONG_TERM_WINDOW, min_periods=1).max().ffill().bfill()
        pe_range_3y = (max_pe_3y - min_pe_3y).replace(0, np.nan)
        
        # 3. 计算估值位置 (仅对盈利公司有意义)
        df['3year_pe_position'] = (df['pe'] - min_pe_3y) / pe_range_3y
        df['3year_pe_position'] = df['3year_pe_position'].fillna(0.5).ffill().bfill().clip(0, 1)
        
        # 4. 为亏损公司设置特殊信号值 -1
        df.loc[df['is_loss'], '3year_pe_position'] = -1
    else:
        df['3year_pe_position'] = 0
        df['is_loss'] = False # 确保列存在

    # 计算转折信号：price_position_cross（1=底部转折，-1=顶部转折，0=无）
    bottom_reversal = (df['pct_change'].shift(1) < 0) & (df['pct_change'] > 0)
    top_reversal = (df['pct_change'].shift(1) > 0) & (df['pct_change'] < 0)
    df['price_position_cross'] = 0
    df.loc[bottom_reversal, 'price_position_cross'] = 1
    df.loc[top_reversal, 'price_position_cross'] = -1

    # 最终检查所有计算字段的缺失值
    calculated_fields = ['MA', 'STD', 'RSD', 'RSD_chg', 'prev_RSD', 
                        'Upper_Band', 'Lower_Band', 'Band_price_position', 
                        'prev_Band_price_position', '90d_price_position', 'prev_90d_price_position',
                        'price_position_cross',
                        '3year_price_position', '3year_pe_position', 'is_loss']
    
    for field in calculated_fields:
        if df[field].isnull().any():
            logging.warning(f"股票 {ts_code} 字段 {field} 存在缺失值，进行填充")
            df[field] = df[field].ffill().bfill()
            if df[field].isnull().any():
                logging.error(f"股票 {ts_code} 字段 {field} 填充后仍有缺失值！")
                # 使用0填充最后的缺失值
                df[field] = df[field].fillna(0)
    
    return df

def calculate_trends(df, annualize=False):
    """
    计算MA和CLOSE的趋势斜率
    
    参数:
        df (DataFrame): 输入数据框
        annualize (bool): 是否使用年化计算，默认为False
    
    返回:
        DataFrame: 添加了MA_slope和CLOSE_slope列的数据框
    """
    if 'MA' not in df.columns or 'close' not in df.columns:
        logging.warning("缺少计算趋势斜率所需的MA或close列，跳过趋势斜率计算")
        return df
    
    # 处理数据的缺失值
    if df['MA'].isnull().any() or df['close'].isnull().any():
        logging.warning(f"MA或close列有缺失值，进行处理")
        df['MA'] = handle_missing_values(df['MA'])
        df['close'] = handle_missing_values(df['close'])
    
    # 初始化趋势斜率数组
    ma_trends = np.zeros(len(df))
    close_trends = np.zeros(len(df))
    
    # 定义合理的斜率上下限
    MAX_REASONABLE_SLOPE = 3.0    # 最大合理斜率（300%）
    MIN_REASONABLE_SLOPE = -3.0   # 最小合理斜率（-300%）
    
    # 记录窗口大小
    # logging.info(f"使用{Config.TREND_WINDOW}天窗口计算MA和CLOSE斜率")
    
    # 记录处理开始
    slope_calculation_start = time.time()
    exceptional_points = 0
    clipped_values = 0
    
    # 计算MA和CLOSE的趋势斜率
    for i in range(len(df)):
        try:
            # 获取可用的窗口数据
            start_idx = max(0, i - Config.TREND_WINDOW + 1)
            ma_data = df['MA'].iloc[start_idx:i + 1].values
            close_data = df['close'].iloc[start_idx:i + 1].values
            
            # 检查数据的有效性
            if len(ma_data) >= 2 and len(close_data) >= 2:
                # 安全检查，防止除以零
                if ma_data[0] != 0:
                    ma_change = (ma_data[-1] - ma_data[0]) / ma_data[0]
                    ma_slope = np.clip(ma_change, MIN_REASONABLE_SLOPE, MAX_REASONABLE_SLOPE)
                else:
                    ma_slope = 0 # 如果期初MA为0，斜率设为0

                # 安全检查，防止除以零
                if close_data[0] != 0:
                    close_change = (close_data[-1] - close_data[0]) / close_data[0]
                    close_slope = np.clip(close_change, MIN_REASONABLE_SLOPE, MAX_REASONABLE_SLOPE)
                else:
                    close_slope = 0 # 如果期初价格为0，斜率设为0
                
                # 记录被限制的值
                if (ma_data[0] != 0 and (ma_change > MAX_REASONABLE_SLOPE or ma_change < MIN_REASONABLE_SLOPE)) or \
                   (close_data[0] != 0 and (close_change > MAX_REASONABLE_SLOPE or close_change < MIN_REASONABLE_SLOPE)):
                    clipped_values += 1
                
                ma_trends[i] = ma_slope
                close_trends[i] = close_slope
            else:
                ma_trends[i] = 0
                close_trends[i] = 0
                
        except Exception as e:
            logging.warning(f"计算斜率时出错，位置:{i}, 错误:{str(e)}")
            exceptional_points += 1
            continue
    
    # 将计算结果添加到DataFrame
    df['MA_slope'] = ma_trends
    df['CLOSE_slope'] = close_trends
    
    # 处理缺失值
    df['MA_slope'] = handle_missing_values(df['MA_slope'])
    df['CLOSE_slope'] = handle_missing_values(df['CLOSE_slope'])
    
    # 记录处理结果
    # calculation_time = time.time() - slope_calculation_start
    # logging.info(f"斜率计算完成，耗时: {calculation_time:.2f}秒")
    # logging.info(f"异常点数量: {exceptional_points}")
    # logging.info(f"被限制的斜率值数量: {clipped_values}")
    
    return df

def detect_divergence(df):
    """检测顶背离和底背离"""
    # 确保输入数据的列存在
    if 'close' not in df.columns or 'MACD' not in df.columns:
        logging.warning("缺少检测背离所需的列(close或MACD)，跳过背离检测")
        df['Divergence_Type'] = '无背离' # 设置默认值
        return df
    
    # 复制相关列以避免修改原始数据
    temp_df = df[['close', 'MACD']].copy()
    
    # 处理输入数据的缺失值
    temp_df = handle_missing_values(temp_df)
    
    # 设置参数
    MIN_DIVERGENCE_RATIO = 0.1  # 最小背离幅度比例
    MIN_PEAK_DISTANCE = 5       # 最小峰值间距
    
    # 计算价格和MACD的变化率
    pre_close = temp_df['close'].shift(1).replace(0, np.nan)
    temp_df['price_change'] = (temp_df['close'] / pre_close) - 1
    
    pre_macd = temp_df['MACD'].shift(1).replace(0, np.nan)
    temp_df['macd_change'] = (temp_df['MACD'] / pre_macd) - 1
    
    # 检测价格峰值和谷值（考虑最小间距）
    peak_condition = (temp_df['close'] > temp_df['close'].shift(1)) & \
                    (temp_df['close'] > temp_df['close'].shift(-1)) & \
                    (temp_df['close'] > temp_df['close'].rolling(window=MIN_PEAK_DISTANCE, center=True).max())
    
    trough_condition = (temp_df['close'] < temp_df['close'].shift(1)) & \
                      (temp_df['close'] < temp_df['close'].shift(-1)) & \
                      (temp_df['close'] < temp_df['close'].rolling(window=MIN_PEAK_DISTANCE, center=True).min())
    
    # 检测背离（考虑幅度变化）
    top_divergence = peak_condition & \
                    (temp_df['MACD'] < temp_df['MACD'].shift(1)) & \
                    (temp_df['MACD'] < temp_df['MACD'].shift(-1)) & \
                    (abs(temp_df['macd_change']) > MIN_DIVERGENCE_RATIO)
    
    bottom_divergence = trough_condition & \
                       (temp_df['MACD'] > temp_df['MACD'].shift(1)) & \
                       (temp_df['MACD'] > temp_df['MACD'].shift(-1)) & \
                       (abs(temp_df['macd_change']) > MIN_DIVERGENCE_RATIO)
    
    # 处理边界条件 - 使用布尔索引而不是iloc
    top_divergence = top_divergence & (temp_df.index > 0) & (temp_df.index < len(temp_df) - 1)
    bottom_divergence = bottom_divergence & (temp_df.index > 0) & (temp_df.index < len(temp_df) - 1)
    
    # 设置背离类型
    df['Divergence_Type'] = np.select(
        [top_divergence, bottom_divergence],
        ['MACD顶背离', 'MACD底背离'],
        default=''
    )
    
    return df

def normalize_date(date_str):
    """
    自动将日期格式统一为 YYYY-MM-DD
    支持以下格式：
    - 20250312
    - 2025-03-12
    """
    if pd.isna(date_str):
        logging.warning(f"日期值为空")
        return None
        
    try:
        # 尝试解析为 YYYYMMDD 格式
        return pd.to_datetime(date_str, format='%Y%m%d').strftime('%Y-%m-%d')
    except ValueError:
        try:
            # 尝试解析为 YYYY-MM-DD 格式
            return pd.to_datetime(date_str, format='%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            # 如果都不匹配，返回 None 并记录日志
            logging.warning(f"无法解析日期: {date_str}")
            return None

def calculate_volatility(df, window=200):
    """计算股价波动率指标
    
    Args:
        df: 包含股票数据的DataFrame
        window: 计算窗口大小，默认为200天
        
    Returns:
        DataFrame: 添加了波动率指标的数据框
    """
    # 确保输入数据的列存在
    if not all(col in df.columns for col in ['close', 'high', 'low']):
        logging.warning("缺少计算波动率所需的列，跳过波动率计算")
        return df
    
    # 预计算常用统计量
    rolling_mean = df['close'].rolling(window=window).mean()
    rolling_std = df['close'].rolling(window=window).std()
    
    # 1. 计算标准差波动率
    df['price_std'] = rolling_std
    df['price_std_ratio'] = rolling_std / rolling_mean
    
    # 2. 计算真实波动幅度(ATR)
    #df['tr1'] = df['high'] - df['low']
    #df['tr2'] = abs(df['high'] - df['close'].shift(1))
    #df['tr3'] = abs(df['low'] - df['close'].shift(1))
    #df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    #df['atr'] = df['tr'].rolling(window=window).mean()
    #df['atr_ratio'] = df['atr'] / df['close']
    
    # 3. 计算价格变化率的标准差
    #df['price_change'] = df['close'].pct_change()
    #df['price_change_std'] = df['price_change'].rolling(window=window).std()
    
    # 4. 计算波动率变化率
    #df['volatility_change'] = df['price_std_ratio'].pct_change()
    
    # 5. 计算波动率趋势
    #df['volatility_trend'] = df['price_std_ratio'].rolling(window=5).mean()
    
    # 6. 计算波动率相对位置
    # 预计算波动率的最大最小值
    #volatility_min = df['price_std_ratio'].rolling(window=window).min()
    #volatility_max = df['price_std_ratio'].rolling(window=window).max()
    #df['volatility_position'] = (df['price_std_ratio'] - volatility_min) / (volatility_max - volatility_min)
    
    # 7. 计算波动率突破信号
    # 预计算波动率的均值和标准差
    #volatility_mean = df['price_std_ratio'].rolling(window=window).mean()
    #volatility_std = df['price_std_ratio'].rolling(window=window).std()
    #df['volatility_breakout'] = 0
    #df.loc[df['price_std_ratio'] > volatility_mean + 2 * volatility_std, 'volatility_breakout'] = 1
    #df.loc[df['price_std_ratio'] < volatility_mean - 2 * volatility_std, 'volatility_breakout'] = -1
    
    # 8. 计算波动率状态
    #df['volatility_state'] = np.select(
    #    [
    #        df['volatility_position'] > 0.8,
    #        df['volatility_position'] < 0.2,
    #        (df['volatility_position'] >= 0.2) & (df['volatility_position'] <= 0.8)
    #    ],
    #    ['高波动', '低波动', '正常波动'],
    #    default='未知'
    #)
    
    # 删除中间计算列
    #df = df.drop(['tr1', 'tr2', 'tr3', 'tr'], axis=1)
    
    return df

def monitor_data_quality(df):
    """
    监控数据质量
    
    参数:
        df (DataFrame): 输入数据框
    
    返回:
        dict: 数据质量报告
    """
    quality_report = {
        'total_rows': len(df),
        'missing_values': df.isnull().sum().to_dict(),
        'rolling_window_coverage': {},
        'data_quality_issues': []
    }
    
    # 预计算滚动窗口统计量
    window_stats = {}
    for window in [20, 90]:
        coverage = df['close'].rolling(window=window, min_periods=1).count()
        window_stats[window] = {
            'coverage': coverage,
            'min': coverage.min(),
            'max': coverage.max(),
            'avg': coverage.mean()
        }
        
        quality_report['rolling_window_coverage'][f'{window}日'] = {
            'min_coverage': window_stats[window]['min'],
            'max_coverage': window_stats[window]['max'],
            'avg_coverage': window_stats[window]['avg']
        }
        
        # 检查数据覆盖是否不足
        if window_stats[window]['min'] < window * 0.5:
            quality_report['data_quality_issues'].append(
                f"{window}日窗口数据覆盖不足，最小覆盖: {window_stats[window]['min']}"
            )
    
    # 检查价格数据的有效性
    if 'close' in df.columns:
        price_issues = []
        # 检查零值或负值
        if (df['close'] <= 0).any():
            price_issues.append("存在零值或负值价格")
        # 检查异常波动
        price_changes = df['close'].pct_change().abs()
        if (price_changes > 0.1).any():
            price_issues.append("存在异常价格波动")
        if price_issues:
            quality_report['data_quality_issues'].extend(price_issues)
    
    # 检查技术指标的有效性
    if 'MA' in df.columns:
        ma_issues = []
        # 检查MA的连续性
        ma_changes = df['MA'].pct_change().abs()
        if (ma_changes > 0.2).any():
            ma_issues.append("MA存在异常变化")
        if ma_issues:
            quality_report['data_quality_issues'].extend(ma_issues)
    
    return quality_report

def process_stock_group(df_group):
    """处理单个股票分组的数据"""
    stock_code = df_group['ts_code'].iloc[0] if not df_group.empty else 'Unknown'
    try:
        df = df_group.copy()

        # 校验数据字段
        for field in Config.REQUIRED_FIELDS:
            if field not in df.columns:
                raise ValueError(f"股票 {stock_code} 缺少必要字段: {field}")

        # 标准化日期格式并排序
        df['trade_date'] = df['trade_date'].apply(normalize_date)
        df = df.dropna(subset=['trade_date']).sort_values('trade_date', ascending=True).reset_index(drop=True)

        # 处理缺失值
        if df.isnull().sum().sum() > 0:
            df = handle_missing_values(df)

        # 计算技术指标
        df = calculate_bollinger_bands(df, stock_code)
        df = calculate_trends(df, annualize=False)
        df = calculate_kdj(df)
        df = calculate_macd(df)
        df = detect_divergence(df)

        # 处理其他字段
        if '主力净量' in df.columns:
            df['主力净量'] = df['主力净量'] / Config.VOLUME_SCALE
        else:
            df['主力净量'] = 0
            
        # 计算成交量相关指标
        if 'vol' in df.columns:
            df['成交量'] = df['vol'] / Config.VOLUME_SCALE
        else:
            df['成交量'] = 0

        # 处理可能的除零情况
        df['主力净量率'] = df['主力净量'] / df['成交量'].replace(0, np.nan)
        df['主力净量率'] = handle_missing_values(df['主力净量率'])
        
        # 计算连续指标
        df['成交量连续增加天数'] = (df['成交量'].diff() > 0).groupby((df['成交量'].diff() <= 0).cumsum()).cumsum()
        df['主力净量连续大于0天数'] = (df['主力净量'] > 0).groupby((df['主力净量'] <= 0).cumsum()).cumsum()
        df['股价连续下跌天数'] = (df['close'].diff() < 0).groupby((df['close'].diff() >= 0).cumsum()).cumsum()
        
        # 计算连板天数
        if 'pct_change' in df.columns:
            df['是否涨停'] = (df['pct_change'] >= 9.5)
        else:
            # 备用逻辑，同样需要防止除以零
            if 'pre_close' in df.columns:
                pre_close_safe = df['pre_close'].replace(0, np.nan)
                pct_change_manual = (df['close'] / pre_close_safe - 1) * 100
                df['是否涨停'] = (pct_change_manual.fillna(0) >= 9.8) # fillna以处理NaN
            else:
                # 如果pre_close列也不存在，无法计算，默认为False
                df['是否涨停'] = False
        
        df['连板天数'] = df['是否涨停'].groupby((~df['是否涨停']).cumsum()).cumsum()
        df.loc[~df['是否涨停'], '连板天数'] = 0
        
        return df

    except Exception as e:
        logging.error(f"处理股票 {stock_code} 数据时出错: {e}")
        return None # 返回None，以便主进程可以忽略此错误组

def write_to_db_with_retry(df, table_name, engine, max_retries=3, retry_delay=1):
    """
    带重试机制的数据库写入函数，使用批量REPLACE INTO提高性能
    
    参数:
        df: 要写入的DataFrame
        table_name: 表名
        engine: 数据库引擎
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
    """
    if df.empty:
        logging.info("数据为空，跳过写入")
        return True
    
    for attempt in range(max_retries):
        try:
            # 添加随机延迟避免并发冲突
            time.sleep(random.uniform(0.1, 0.5))
            
            # 使用批量REPLACE INTO，大幅提高性能
            with engine.begin() as conn:
                # 准备批量数据
                columns = df.columns.tolist()
                quoted_columns = [f"`{col}`" for col in columns]
                
                # 构建批量插入的VALUES子句
                value_rows = []
                for _, row in df.iterrows():
                    values = []
                    for col in columns:
                        val = row[col]
                        if pd.isna(val):
                            values.append('NULL')
                        elif isinstance(val, str):
                            # 转义单引号
                            escaped_val = val.replace("'", "''")
                            values.append(f"'{escaped_val}'")
                        else:
                            values.append(str(val))
                    value_rows.append(f"({', '.join(values)})")
                
                # 构建批量REPLACE INTO语句
                replace_sql = f"REPLACE INTO {table_name} ({', '.join(quoted_columns)}) VALUES {', '.join(value_rows)}"
                
                # 执行批量插入
                conn.execute(text(replace_sql))
                affected_rows = len(df)
                
                logging.info(f"成功批量写入 {affected_rows} 条数据到 {table_name}（使用批量REPLACE INTO）")
                return True
            
        except Exception as e:
            if "Deadlock" in str(e) or "1213" in str(e):
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"数据库死锁，第 {attempt + 1} 次重试，等待 {wait_time:.2f} 秒...")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error(f"数据库写入失败，已重试 {max_retries} 次: {e}")
                    return False
            elif "Duplicate entry" in str(e) or "1062" in str(e):
                logging.warning(f"检测到重复数据，但REPLACE INTO应该已处理: {e}")
                return True  # 重复数据不算错误
            else:
                logging.error(f"数据库写入出错: {e}")
                return False
    
    return False

def validate_data_before_write(df, table_name):
    """
    验证数据格式，确保可以安全写入数据库（优化版本）
    
    参数:
        df: 要验证的DataFrame
        table_name: 表名
    
    返回:
        bool: 数据是否有效
    """
    try:
        # 检查必需字段
        required_fields = ['ts_code', 'trade_date', 'close']
        for field in required_fields:
            if field not in df.columns:
                logging.error(f"缺少必需字段: {field}")
                return False
        
        # 快速检查空值（只检查必需字段）
        null_counts = df[required_fields].isnull().sum()
        if null_counts.sum() > 0:
            logging.warning(f"发现空值: {null_counts.to_dict()}")
            # 删除包含空值的行
            df.dropna(subset=required_fields, inplace=True)
            logging.info(f"删除空值后剩余 {len(df)} 条记录")
        
        # 检查重复数据（只检查主键字段）
        duplicates = df.duplicated(subset=['ts_code', 'trade_date']).sum()
        if duplicates > 0:
            logging.warning(f"发现 {duplicates} 条重复数据，将保留第一条")
            df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='first', inplace=True)
        
        return True
        
    except Exception as e:
        logging.error(f"数据验证失败: {e}")
        return False

def process_stock_data():
    """读取单个大数据文件，并行处理所有股票数据，然后保存为单个输出文件"""
    logging.info(f"开始从 MySQL 读取数据...")
    
    # 配置数据库连接池，优化并发性能
    engine = db_utils.get_engine()
    
    # 设置连接池参数，优化并发性能
    if hasattr(engine, 'pool'):
        engine.pool.size = 10  # 增加连接池大小
        engine.pool.max_overflow = 20  # 增加最大溢出连接数
        engine.pool.timeout = 30
        engine.pool.recycle = 3600  # 1小时后回收连接
        engine.pool.pre_ping = True  # 连接前检查连接有效性
    
    inspector = inspect(engine)
    if not inspector.has_table('stock_daily_processed'):
        logging.info('stock_daily_processed表不存在，将分批从原始数据生成并写入...')
        # 1. 先查所有股票代码
        try:
            ts_codes = pd.read_sql('SELECT DISTINCT ts_code FROM stock_daily', con=engine)['ts_code'].tolist()
        except Exception as e:
            logging.error(f"从 MySQL 查询股票代码时出错: {e}")
            return
        logging.info(f"共找到 {len(ts_codes)} 只股票待处理。")
        processed_groups = []
        for ts_code in tqdm(ts_codes, desc="分批处理股票", ncols=80, colour='green'):
            try:
                df = pd.read_sql(f"SELECT * FROM stock_daily WHERE ts_code='{ts_code}'", con=engine)
            except Exception as e:
                logging.warning(f"读取股票 {ts_code} 数据时出错: {e}")
                continue
            result = process_stock_group(df)
            if result is not None:
                processed_groups.append(result)
        logging.info("所有股票处理完成。")
        if not processed_groups:
            logging.error("没有数据被成功处理，程序终止。")
            return
        logging.info("开始合并处理后的数据...")
        final_df = pd.concat(processed_groups, ignore_index=True)
        logging.info(f"数据合并完成，最终总行数: {len(final_df)}")
        logging.info("开始写入数据库...")
        final_df.to_sql('stock_daily_processed', con=engine, if_exists='append', index=False)
        logging.info(f'首次写入，已创建表并写入 {len(final_df)} 条数据到 stock_daily_processed')
        return
    
    # 如果表已存在，执行增量更新
    logging.info("stock_daily_processed表已存在，执行增量更新...")
    try:
        df = pd.read_sql('SELECT * FROM stock_daily', con=engine)
    except Exception as e:
        logging.error(f"从 MySQL 读取原始数据时出错: {e}")
        return
    logging.info(f"数据读取完毕，总行数: {len(df)}")
    
    # 按 'ts_code' 分组，为并行处理准备数据
    stock_groups = [group for _, group in df.groupby('ts_code')]
    logging.info(f"共找到 {len(stock_groups)} 只股票待处理。")
    processed_groups = []
    
    # 使用多进程处理，显示进度条
    logging.info("开始多进程处理股票数据...")
    # 增加并发数量，提高处理速度
    max_workers = max(1, min(cpu_count() // 2, 8))  # 最多8个进程
    logging.info(f"使用 {max_workers} 个进程进行数据处理")
    
    with Pool(max_workers) as pool:
        with tqdm(total=len(stock_groups), desc="处理股票数据", ncols=80, colour='green') as pbar:
            for result in pool.imap_unordered(process_stock_group, stock_groups):
                if result is not None:
                    processed_groups.append(result)
                pbar.update()
    
    logging.info("所有股票处理完成。")
    if not processed_groups:
        logging.error("没有数据被成功处理，程序终止。")
        return
    
    # 合并处理后的数据
    logging.info("开始合并所有处理过的数据...")
    try:
        final_df = pd.concat(processed_groups, ignore_index=True)
        logging.info(f"数据合并完成，最终总行数: {len(final_df)}")
    except Exception as e:
        logging.error(f"数据合并失败: {e}")
        return
    
    # 分批去重写入，按trade_date分组
    logging.info("开始分批写入数据库...")
    batch_count = 0
    total_new = 0
    failed_dates = []
    
    # 获取所有日期并排序
    dates = sorted(final_df['trade_date'].unique())
    logging.info(f"共有 {len(dates)} 个交易日需要处理")
    
    # 批量处理，每批处理多个日期
    batch_size = 10  # 每批处理10个日期
    for i in range(0, len(dates), batch_size):
        batch_dates = dates[i:i + batch_size]
        batch_data = final_df[final_df['trade_date'].isin(batch_dates)]
        
        logging.info(f"处理批次 {i//batch_size + 1}，包含 {len(batch_dates)} 个日期，数据量: {len(batch_data)}")
        
        if not batch_data.empty:
            # 验证数据格式
            if not validate_data_before_write(batch_data, 'stock_daily_processed'):
                logging.error(f"批次 {i//batch_size + 1} 数据验证失败，跳过写入")
                failed_dates.extend(batch_dates)
                continue
            
            # 使用批量REPLACE INTO写入
            if write_to_db_with_retry(batch_data, 'stock_daily_processed', engine):
                total_new += len(batch_data)
                logging.info(f"批次 {i//batch_size + 1} 写入完成")
            else:
                failed_dates.extend(batch_dates)
                logging.error(f"批次 {i//batch_size + 1} 写入失败")
        else:
            logging.info(f"批次 {i//batch_size + 1} 无数据")
        
        batch_count += 1
    
    logging.info(f'分批写入完成，共处理 {batch_count} 个日期批次，累计追加新数据 {total_new} 条到 stock_daily_processed')
    if failed_dates:
        logging.warning(f"以下日期写入失败: {failed_dates}")

# 主函数
def main():
    """主函数"""
    start_time = time.time()
    
    try:
        # 检查并设置默认配置
        check_config()
        
        # 配置日志记录器
        if not logging.getLogger().hasHandlers():
            setup_logging()

        logging.info("=== 开始处理股票数据 ===")
        process_stock_data()  # 不再需要传入CSV路径
        logging.info("=== 股票数据处理完成 ===")

    except KeyboardInterrupt:
        logging.warning("程序被用户中断")
        print("\n程序被用户中断")
    except Exception as e:
        logging.error(f"程序执行出错: {e}")
        print(f"\n程序执行出错: {e}")
    finally:
        end_time = time.time()
        total_time = end_time - start_time
        print(f"=== 程序结束，总花费时间: {total_time:.2f} 秒 ===")

# 配置检查
def check_config():
    """检查必要的配置参数，如果不存在则设置默认值"""
    required_configs = {
        'MIN_PRICE_WINDOW': 90,
        'TREND_WINDOW': 10,
        'VOLUME_SCALE': 100,
        'DIVERGENCE_THRESHOLD': 0.1,
        'LOG_FILE': None,  # 默认不写入文件
        'LOG_LEVEL': logging.INFO,
        'OUTPUT_DIR': 'stock_data',
        'PRICE_CHANGE_THRESHOLD': 0.1,
        'MA_CHANGE_THRESHOLD': 0.2,
        'VOLUME_CHANGE_THRESHOLD': 2.0,
        'RSD_LIMIT': 50.0,
        'SLOPE_LIMIT': 3.0
    }
    
    for config_name, default_value in required_configs.items():
        if not hasattr(Config, config_name):
            setattr(Config, config_name, default_value)
            logging.info(f"配置 '{config_name}' 未找到, 使用默认值: {default_value}")

if __name__ == "__main__":
    main()

        