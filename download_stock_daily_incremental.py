import tushare as ts
import datetime
import os
import logging
import pandas as pd
import shutil
import numpy as np
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_exponential
import db_utils
from sqlalchemy import inspect, text
from logging_config import setup_logging
import random

# 忽略FutureWarning警告
warnings.filterwarnings('ignore', category=FutureWarning)
# 忽略Pandas的SettingWithCopyWarning
warnings.filterwarnings('ignore', message='.*SettingWithCopyWarning.*')

# 配置简洁的日志
setup_logging(level=logging.INFO)

# 增加配置常量
MAX_RETRIES = 3  # 最大重试次数
API_RATE_LIMIT = 500  # 每分钟请求限制
BATCH_SIZE = 50  # 批量处理大小

# 全局变量
pro = None

def init_tushare():
    """初始化 Tushare API"""
    global pro
    if pro is None:
        ts.set_token('dd29d91ca9f8577814389ee9e722991fe05df214e1755d82702f956d')
        pro = ts.pro_api()
    return pro

# 增加速率限制器
class RateLimiter:
    def __init__(self, rate_limit):
        self.rate_limit = rate_limit
        self.last_call = time.time()
        
    def wait(self):
        elapsed = time.time() - self.last_call
        wait_time = max(60/self.rate_limit - elapsed, 0)
        time.sleep(wait_time)
        self.last_call = time.time()

rate_limiter = RateLimiter(API_RATE_LIMIT)

@retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=4, max=10))
def safe_api_call(api_func, *args, **kwargs):
    """带重试和速率限制的API调用封装"""
    rate_limiter.wait()
    return api_func(*args, **kwargs)

def get_all_stock_codes():
    """获取所有A股股票代码，返回符合要求的格式，并过滤ST股票"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        # 获取所有股票列表
        stock_list = pro.stock_basic(exchange='', list_status='L')
        
        # 过滤ST股票（股票名称中包含'ST'或'*ST'的股票）
        stock_list = stock_list[~stock_list['name'].str.contains('ST')]
        
        # 筛选出以60、30、00开头的股票代码，并添加交易所后缀
        stock_codes = [
            f"{row['symbol']}.SH" if row['symbol'].startswith(('60')) else f"{row['symbol']}.SZ"
            for _, row in stock_list[stock_list['symbol'].str.match('^(60|30|00)')].iterrows()
        ]
        
        logging.info(f"获取到 {len(stock_codes)} 只非ST股票")
        return stock_codes
    except Exception as e:
        logging.error(f"获取股票列表失败: {e}")
        return []

def get_completely_missing_dates(engine, start_date, end_date):
    """获取指定日期范围内完全缺失的交易日（该日期没有任何股票数据）"""
    try:
        # 获取所有交易日
        all_trading_dates = get_trading_dates(start_date, end_date)
        
        completely_missing_dates = []
        
        for trade_date in all_trading_dates:
            # 查询该日期有多少只股票的数据
            query = f"""
            SELECT COUNT(DISTINCT ts_code) as stock_count 
            FROM stock_daily 
            WHERE trade_date = '{trade_date}'
            """
            result = pd.read_sql(query, con=engine)
            stock_count = result.iloc[0]['stock_count']
            
            # 如果该日期没有任何股票数据，则认为是完全缺失
            if stock_count == 0:
                completely_missing_dates.append(trade_date)
        
        return completely_missing_dates
        
    except Exception as e:
        logging.error(f"获取完全缺失日期失败: {e}")
        return []

def get_trading_dates(start_date, end_date):
    """获取指定日期范围内的交易日"""
    try:
        pro = init_tushare()
        trade_cal = pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        trading_dates = trade_cal[trade_cal['is_open'] == 1]['cal_date'].tolist()
        return trading_dates
    except Exception as e:
        logging.error(f"获取交易日历失败: {e}")
        return []

def write_to_db_safe(df, table_name, engine, max_retries=3):
    """安全的数据库写入函数，处理重复数据"""
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
                    
                    # 使用REPLACE INTO，如果存在重复数据则替换
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

def download_daily_data_by_date_batch(trade_date, engine):
    """按日期批量下载所有股票数据（更高效的方式）"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        logging.info(f"开始批量下载 {trade_date} 的股票数据")
        
        # 1. 批量下载日线数据
        logging.info(f"下载 {trade_date} 的日线数据...")
        df_daily = safe_api_call(pro.bak_daily, trade_date=trade_date)
        
        if df_daily is None or df_daily.empty:
            logging.warning(f"日期 {trade_date} 没有日线数据")
            return 0
        
        # 过滤非ST股票
        df_daily = df_daily[~df_daily['name'].str.contains('ST', na=False)]
        
        # 2. 批量下载资金流向数据
        logging.info(f"下载 {trade_date} 的资金流向数据...")
        df_moneyflow = safe_api_call(pro.moneyflow, trade_date=trade_date)
        
        # 3. 合并数据
        if df_moneyflow is not None and not df_moneyflow.empty:
            # 过滤非ST股票的资金流向数据
            df_moneyflow = df_moneyflow[~df_moneyflow['ts_code'].isin(df_daily['ts_code'])]
            
            # 合并日线和资金流向数据
            df_merged = pd.merge(df_daily, df_moneyflow, on=['ts_code', 'trade_date'], how='left')
            
            # 计算主力净量
            df_merged['buy_lg_vol'] = df_merged['buy_lg_vol'].fillna(0)
            df_merged['sell_lg_vol'] = df_merged['sell_lg_vol'].fillna(0)
            df_merged['buy_elg_vol'] = df_merged['buy_elg_vol'].fillna(0)
            df_merged['sell_elg_vol'] = df_merged['sell_elg_vol'].fillna(0)
            
            df_merged['主力净量'] = (
                df_merged['buy_lg_vol'] - df_merged['sell_lg_vol'] +
                df_merged['buy_elg_vol'] - df_merged['sell_elg_vol']
            )
            
            # 计算主力净量率
            df_merged['vol'] = df_merged['vol'].fillna(0)
            df_merged['主力净量率'] = np.where(
                df_merged['vol'] > 0, 
                df_merged['主力净量'] / df_merged['vol'], 
                0
            )
            
            # 选择需要的字段
            fields_to_keep = [
                'ts_code', 'trade_date', 'name', 'pct_change', 'close', 'open', 'high', 'low', 'pre_close',
                'vol_ratio', 'turn_over', 'vol', 'amount', 'total_share', 'float_share',
                'pe', 'industry', 'area', 'float_mv', 'total_mv', '主力净量', '主力净量率'
            ]
            existing_fields = [field for field in fields_to_keep if field in df_merged.columns]
            df_final = df_merged[existing_fields].copy()
            
        else:
            # 如果没有资金流向数据，只保存日线数据
            logging.warning(f"日期 {trade_date} 没有资金流向数据，只保存日线数据")
            fields_to_keep = [
                'ts_code', 'trade_date', 'name', 'pct_change', 'close', 'open', 'high', 'low', 'pre_close',
                'vol_ratio', 'turn_over', 'vol', 'amount', 'total_share', 'float_share',
                'pe', 'industry', 'area', 'float_mv', 'total_mv'
            ]
            existing_fields = [field for field in fields_to_keep if field in df_daily.columns]
            df_final = df_daily[existing_fields].copy()
            df_final['主力净量'] = np.nan
            df_final['主力净量率'] = np.nan
        
        # 4. 写入数据库
        if not df_final.empty:
            try:
                if write_to_db_safe(df_final, 'stock_daily', engine):
                    logging.info(f"日期 {trade_date} 成功下载并保存 {len(df_final)} 条数据")
                    return len(df_final)
                else:
                    logging.error(f"保存日期 {trade_date} 数据失败")
                    return 0
            except Exception as e:
                logging.error(f"保存日期 {trade_date} 数据时出错: {e}")
                return 0
        else:
            logging.warning(f"日期 {trade_date} 处理后无有效数据")
            return 0
            
    except Exception as e:
        logging.error(f"下载日期 {trade_date} 数据时出错: {e}")
        return 0

def create_stock_daily_table(engine):
    """创建stock_daily表（如果不存在）"""
    try:
        inspector = inspect(engine)
        if not inspector.has_table('stock_daily'):
            logging.info("创建stock_daily表...")
            
            create_table_sql = """
            CREATE TABLE stock_daily (
                ts_code VARCHAR(20),
                trade_date DATE,
                name VARCHAR(50),
                pct_change DECIMAL(10,4),
                close DECIMAL(10,2),
                open DECIMAL(10,2),
                high DECIMAL(10,2),
                low DECIMAL(10,2),
                pre_close DECIMAL(10,2),
                vol_ratio DECIMAL(10,4),
                turn_over DECIMAL(10,4),
                vol DECIMAL(20,2),
                amount DECIMAL(20,2),
                total_share DECIMAL(20,2),
                float_share DECIMAL(20,2),
                pe DECIMAL(10,4),
                industry VARCHAR(50),
                area VARCHAR(50),
                float_mv DECIMAL(20,2),
                total_mv DECIMAL(20,2),
                主力净量 DECIMAL(20,2),
                主力净量率 DECIMAL(10,4),
                PRIMARY KEY (ts_code, trade_date)
            )
            """
            
            with engine.begin() as conn:
                conn.execute(text(create_table_sql))
            
            logging.info("stock_daily表创建完成")
        else:
            logging.info("stock_daily表已存在")
            
    except Exception as e:
        logging.error(f"创建表失败: {e}")
        raise

def process_incremental_download():
    """增量下载股票数据（混合方案）"""
    logging.info("开始增量下载股票数据...")
    
    # 初始化数据库连接
    engine = db_utils.get_engine()
    
    # 确保表存在
    create_stock_daily_table(engine)
    
    # 定义日期范围：最近30天
    today = datetime.datetime.today()
    start_date = (today - datetime.timedelta(days=30)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    logging.info(f"下载日期范围: {start_date} 到 {end_date}")
    
    # 获取完全缺失的日期（该日期没有任何股票数据）
    completely_missing_dates = get_completely_missing_dates(engine, start_date, end_date)
    
    if not completely_missing_dates:
        logging.info("所有日期数据都已完整，无需下载")
        return
    
    logging.info(f"发现 {len(completely_missing_dates)} 个完全缺失的交易日，开始下载")
    
    total_downloaded = 0
    
    # 按日期下载数据
    for trade_date in tqdm(completely_missing_dates, desc="下载缺失日期数据"):
        try:
            downloaded_count = download_daily_data_by_date_batch(trade_date, engine)
            total_downloaded += downloaded_count
            
            # 日期间延迟
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"处理日期 {trade_date} 时出错: {e}")
            continue
    
    logging.info(f"增量下载完成！")
    logging.info(f"处理日期数: {len(completely_missing_dates)}")
    logging.info(f"总下载数据量: {total_downloaded} 条")

def main():
    """主函数"""
    try:
        logging.info("=== 开始增量下载股票日线数据 ===")
        process_incremental_download()
        logging.info("=== 增量下载完成 ===")
    except Exception as e:
        logging.error(f"程序运行出错: {e}")
        raise

if __name__ == "__main__":
    main() 