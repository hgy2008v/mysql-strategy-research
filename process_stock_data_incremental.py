import pandas as pd
import numpy as np
import os
import logging
import time
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import db_utils
from sqlalchemy import inspect
import random
from sqlalchemy import text
import gc

# 参数配置
class Config:
    # 数据处理参数
    MIN_PRICE_WINDOW = 90
    TREND_WINDOW = 10
    VOLUME_SCALE = 100
    LONG_TERM_WINDOW = 756
    
    # 技术指标参数
    MACD_SHORT_WINDOW = 12
    MACD_LONG_WINDOW = 26
    MACD_SIGNAL_WINDOW = 9
    KDJ_WINDOW = 9
    RSI_PERIOD = 14
    BBI_WINDOWS = [3, 6, 12, 24]
    
    # 输入输出配置
    REQUIRED_FIELDS = ['trade_date', 'open', 'high', 'low', 'close', 'vol']
    
    # 性能优化参数
    BATCH_SIZE = 100  # 每批处理的股票数量
    MAX_WORKERS = 4   # 最大进程数

# 配置日志
def setup_logging():
    """配置日志输出"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )

def handle_missing_values(df, method='interpolate'):
    """处理DataFrame或Series中的缺失值"""
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
            df = df.ffill().bfill()
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
                df[col] = df[col].ffill().bfill()
    
    return df

def calculate_bollinger_bands(df, ts_code='Unknown'):
    """计算布林带指标（简化版本）"""
    if 'close' not in df.columns:
        return df
    
    # 计算中轨（MA）
    df['MA'] = df['close'].rolling(window=20, min_periods=1).mean()
    df['MA'] = df['MA'].ffill().bfill()
    
    # 计算标准差
    df['STD'] = df['close'].rolling(window=20, min_periods=1).std()
    df['STD'] = df['STD'].ffill().bfill()
    
    # 计算RSD
    df['RSD'] = df.apply(lambda row: 0 if row['MA'] == 0 else (row['STD'] / row['MA']) * 100, axis=1)
    df['RSD'] = df['RSD'].ffill().bfill()
    
    # 计算布林带上下轨
    df['Upper_Band'] = df['MA'] + (df['STD'] * 2)
    df['Lower_Band'] = df['MA'] - (df['STD'] * 2)
    df['Upper_Band'] = df['Upper_Band'].ffill().bfill()
    df['Lower_Band'] = df['Lower_Band'].ffill().bfill()
    
    # 计算价格位置
    df['Band_price_position'] = df.apply(
        lambda row: 0.5 if (row['Upper_Band'] - row['Lower_Band']) == 0 
        else (row['close'] - row['Lower_Band']) / (row['Upper_Band'] - row['Lower_Band']), 
        axis=1
    )
    df['Band_price_position'] = df['Band_price_position'].ffill().bfill()
    
    return df

def calculate_kdj(df):
    """计算 KDJ 指标（简化版本）"""
    if not all(col in df.columns for col in ['low', 'high', 'close']):
        return df
    
    temp_df = df[['low', 'high', 'close']].copy()
    temp_df = handle_missing_values(temp_df)
    
    low_min = temp_df['low'].rolling(window=Config.KDJ_WINDOW, min_periods=1).min()
    high_max = temp_df['high'].rolling(window=Config.KDJ_WINDOW, min_periods=1).max()
    
    denominator = high_max - low_min
    denominator = denominator.replace(0, np.nan)
    rsv = (temp_df['close'] - low_min) / denominator * 100
    
    K = rsv.ewm(com=2, adjust=False).mean()
    D = K.ewm(com=2, adjust=False).mean()
    
    K = handle_missing_values(K)
    D = handle_missing_values(D)
    
    df['K'] = K
    df['D'] = D
    
    return df

def calculate_macd(df):
    """计算 MACD 指标（简化版本）"""
    if 'close' not in df.columns:
        return df
    
    temp_df = df[['close']].copy()
    temp_df = handle_missing_values(temp_df)
    
    df['EMA_short'] = temp_df['close'].ewm(span=Config.MACD_SHORT_WINDOW, adjust=False).mean()
    df['EMA_long'] = temp_df['close'].ewm(span=Config.MACD_LONG_WINDOW, adjust=False).mean()
    
    df['EMA_short'] = handle_missing_values(df['EMA_short'])
    df['EMA_long'] = handle_missing_values(df['EMA_long'])
    
    df['MACD'] = df['EMA_short'] - df['EMA_long']
    df['MACD'] = handle_missing_values(df['MACD'])
    
    df['Signal'] = df['MACD'].ewm(span=Config.MACD_SIGNAL_WINDOW, adjust=False).mean()
    df['Signal'] = handle_missing_values(df['Signal'])
    
    return df

def normalize_date(date_str):
    """标准化日期格式"""
    if pd.isna(date_str):
        return None
    try:
        return pd.to_datetime(date_str, format='%Y%m%d').strftime('%Y-%m-%d')
    except ValueError:
        try:
            return pd.to_datetime(date_str, format='%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            return None

def process_stock_group_simple(df_group):
    """处理单个股票分组的数据（简化版本）"""
    stock_code = df_group['ts_code'].iloc[0] if not df_group.empty else 'Unknown'
    try:
        df = df_group.copy()

        # 校验数据字段
        for field in Config.REQUIRED_FIELDS:
            if field not in df.columns:
                return None

        # 标准化日期格式并排序
        df['trade_date'] = df['trade_date'].apply(normalize_date)
        df = df.dropna(subset=['trade_date']).sort_values('trade_date', ascending=True).reset_index(drop=True)

        # 处理缺失值
        if df.isnull().sum().sum() > 0:
            df = handle_missing_values(df)

        # 计算技术指标（只保留核心指标）
        df = calculate_bollinger_bands(df, stock_code)
        df = calculate_kdj(df)
        df = calculate_macd(df)

        # 处理其他字段
        if '主力净量' in df.columns:
            df['主力净量'] = df['主力净量'] / Config.VOLUME_SCALE
        else:
            df['主力净量'] = 0
            
        if 'vol' in df.columns:
            df['成交量'] = df['vol'] / Config.VOLUME_SCALE
        else:
            df['成交量'] = 0

        # 计算连续指标
        df['成交量连续增加天数'] = (df['成交量'].diff() > 0).groupby((df['成交量'].diff() <= 0).cumsum()).cumsum()
        df['主力净量连续大于0天数'] = (df['主力净量'] > 0).groupby((df['主力净量'] <= 0).cumsum()).cumsum()
        
        return df

    except Exception as e:
        logging.error(f"处理股票 {stock_code} 数据时出错: {e}")
        return None

def write_to_db_optimized(df, table_name, engine, max_retries=3):
    """优化的数据库写入函数"""
    if df.empty:
        return True
    
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(0.1, 0.3))
            
            with engine.begin() as conn:
                columns = df.columns.tolist()
                quoted_columns = [f"`{col}`" for col in columns]
                
                # 分批处理，避免单次插入过多数据
                batch_size = 1000
                for i in range(0, len(df), batch_size):
                    batch_df = df.iloc[i:i + batch_size]
                    
                    value_rows = []
                    for _, row in batch_df.iterrows():
                        values = []
                        for col in columns:
                            val = row[col]
                            if pd.isna(val):
                                values.append('NULL')
                            elif isinstance(val, str):
                                escaped_val = val.replace("'", "''")
                                values.append(f"'{escaped_val}'")
                            else:
                                values.append(str(val))
                        value_rows.append(f"({', '.join(values)})")
                    
                    replace_sql = f"REPLACE INTO {table_name} ({', '.join(quoted_columns)}) VALUES {', '.join(value_rows)}"
                    conn.execute(text(replace_sql))
                
                logging.info(f"成功写入 {len(df)} 条数据到 {table_name}")
                return True
            
        except Exception as e:
            if "Deadlock" in str(e) or "1213" in str(e):
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    logging.warning(f"数据库死锁，第 {attempt + 1} 次重试，等待 {wait_time:.2f} 秒...")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error(f"数据库写入失败，已重试 {max_retries} 次: {e}")
                    return False
            else:
                logging.error(f"数据库写入出错: {e}")
                return False
    
    return False

def get_unprocessed_stocks(engine):
    """获取未处理的股票列表"""
    try:
        # 获取原始数据中的所有股票代码
        query = "SELECT DISTINCT ts_code FROM stock_daily"
        all_stocks = pd.read_sql(query, con=engine)['ts_code'].tolist()
        
        # 获取已处理数据中的所有股票代码
        query = "SELECT DISTINCT ts_code FROM stock_daily_processed"
        processed_stocks = pd.read_sql(query, con=engine)['ts_code'].tolist()
        
        # 找出未处理的股票
        unprocessed_stocks = list(set(all_stocks) - set(processed_stocks))
        
        logging.info(f"总股票数: {len(all_stocks)}")
        logging.info(f"已处理股票数: {len(processed_stocks)}")
        logging.info(f"未处理股票数: {len(unprocessed_stocks)}")
        
        return unprocessed_stocks
        
    except Exception as e:
        logging.error(f"获取未处理股票列表失败: {e}")
        return []

def process_incremental_data():
    """增量处理股票数据"""
    logging.info("开始增量处理股票数据...")
    
    engine = db_utils.get_engine()
    
    # 检查表是否存在
    inspector = inspect(engine)
    if not inspector.has_table('stock_daily_processed'):
        logging.info('stock_daily_processed表不存在，创建表...')
        # 创建表结构
        create_table_sql = """
        CREATE TABLE stock_daily_processed (
            ts_code VARCHAR(20),
            trade_date DATE,
            close DECIMAL(10,2),
            open DECIMAL(10,2),
            high DECIMAL(10,2),
            low DECIMAL(10,2),
            vol DECIMAL(20,2),
            pct_change DECIMAL(10,4),
            MA DECIMAL(10,2),
            STD DECIMAL(10,2),
            RSD DECIMAL(10,2),
            Upper_Band DECIMAL(10,2),
            Lower_Band DECIMAL(10,2),
            Band_price_position DECIMAL(10,4),
            K DECIMAL(10,4),
            D DECIMAL(10,4),
            MACD DECIMAL(10,4),
            Signal DECIMAL(10,4),
            主力净量 DECIMAL(20,2),
            成交量 DECIMAL(20,2),
            成交量连续增加天数 INT,
            主力净量连续大于0天数 INT,
            PRIMARY KEY (ts_code, trade_date)
        )
        """
        with engine.begin() as conn:
            conn.execute(text(create_table_sql))
        logging.info("表创建完成")
    
    # 获取未处理的股票列表
    unprocessed_stocks = get_unprocessed_stocks(engine)
    
    if not unprocessed_stocks:
        logging.info("所有股票都已处理完成")
        return
    
    # 分批处理未处理的股票
    total_processed = 0
    
    for i in range(0, len(unprocessed_stocks), Config.BATCH_SIZE):
        batch_stocks = unprocessed_stocks[i:i + Config.BATCH_SIZE]
        logging.info(f"处理批次 {i//Config.BATCH_SIZE + 1}/{(len(unprocessed_stocks) + Config.BATCH_SIZE - 1)//Config.BATCH_SIZE}，股票数量: {len(batch_stocks)}")
        
        # 读取当前批次的股票数据
        stock_codes_str = "', '".join(batch_stocks)
        query = f"SELECT * FROM stock_daily WHERE ts_code IN ('{stock_codes_str}')"
        
        try:
            df = pd.read_sql(query, con=engine)
            logging.info(f"读取到 {len(df)} 条数据")
        except Exception as e:
            logging.error(f"读取批次数据失败: {e}")
            continue
        
        if df.empty:
            logging.warning("当前批次无数据")
            continue
        
        # 按股票代码分组
        stock_groups = [group for _, group in df.groupby('ts_code')]
        
        # 使用多进程处理当前批次
        with Pool(Config.MAX_WORKERS) as pool:
            batch_results = []
            for result in tqdm(pool.imap_unordered(process_stock_group_simple, stock_groups), 
                              total=len(stock_groups), desc=f"批次{i//Config.BATCH_SIZE + 1}"):
                if result is not None:
                    batch_results.append(result)
        
        # 合并当前批次结果
        if batch_results:
            batch_df = pd.concat(batch_results, ignore_index=True)
            logging.info(f"批次 {i//Config.BATCH_SIZE + 1} 处理完成，数据量: {len(batch_df)}")
            
            # 写入数据库
            if write_to_db_optimized(batch_df, 'stock_daily_processed', engine):
                total_processed += len(batch_df)
                logging.info(f"批次 {i//Config.BATCH_SIZE + 1} 写入完成")
            else:
                logging.error(f"批次 {i//Config.BATCH_SIZE + 1} 写入失败")
        
        # 强制垃圾回收
        gc.collect()
    
    logging.info(f'增量处理完成，累计处理 {total_processed} 条数据')

def main():
    """主函数"""
    start_time = time.time()
    
    try:
        setup_logging()
        logging.info("=== 开始增量处理股票数据 ===")
        process_incremental_data()
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

if __name__ == "__main__":
    main() 