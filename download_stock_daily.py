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

# 忽略FutureWarning警告
warnings.filterwarnings('ignore', category=FutureWarning)

# Configure logging with timestamp and log level
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# 增加配置常量
MAX_RETRIES = 3  # 最大重试次数
API_RATE_LIMIT = 500  # 每分钟请求限制，从200调整为500
BATCH_SIZE = 100  # 批量处理大小

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

def clear_file(file_path):
    """
    Delete the file if it exists.
    """
    if os.path.exists(file_path):
        os.remove(file_path)
        logging.info(f"Cleared existing file: {file_path}")

def clear_folder(folder_path):
    """
    Clears the specified folder by deleting all files and subdirectories.
    If the folder does not exist, it will be created.
    
    Parameters:
      folder_path: The target folder path.
    """
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                logging.error(f"Failed to delete {file_path}. Reason: {e}")
    else:
        os.makedirs(folder_path)

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

def download_data_in_date_range(api_func, api_name, start_date, end_date, **kwargs):
    """
    通过按天循环，获取指定日期范围内的所有数据。
    
    参数:
      api_func: 要调用的Tushare API函数 (例如, pro.daily)。
      api_name: API函数的名称 (用于显示进度条)。
      start_date: 开始日期 (YYYYMMDD)。
      end_date: 结束日期 (YYYYMMDD)。
      **kwargs: 传递给API函数的其他参数。
    """
    # 初始化 tushare
    pro = init_tushare()
    
    all_data = []
    # 生成日期范围
    trade_dates = pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
    trade_dates = trade_dates[trade_dates.is_open == 1]['cal_date']

    for date in tqdm(trade_dates, desc=f"下载 {api_name} 数据"):
        try:
            df = safe_api_call(api_func, trade_date=date, **kwargs)
            if df is not None and not df.empty:
                all_data.append(df)
        except Exception as e:
            logging.error(f"在日期 {date} 下载数据时失败: {e}")
            
    if not all_data:
        return pd.DataFrame()
        
    return pd.concat(all_data, ignore_index=True)

def process_stock_data(stock_codes, output_dir):
    """处理并合并所有指定股票的数据，并输出为单个文件"""
    # 初始化 tushare
    pro = init_tushare()
    
    # 定义日期范围：过去约3.7个月（110天）
    today = datetime.datetime.today()
    start_date = (today - datetime.timedelta(days=1100)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    
    logging.info(f"开始下载日期范围: {start_date} 到 {end_date}")
    
    try:
        # 1. 下载日线数据 (按天循环, 使用 bak_daily)
        logging.info("正在下载备用日线数据 (bak_daily)...")
        df_daily = download_data_in_date_range(pro.bak_daily, 'bak_daily', start_date, end_date)
        
        if df_daily.empty:
            logging.error("未获取到日线数据，程序终止。")
            return
        
        # 根据用户请求，只保留特定字段
        fields_to_keep = [
            'ts_code', 'trade_date', 'name', 'pct_change', 'close', 'open', 'high', 'low', 'pre_close',
            'vol_ratio', 'turn_over', 'vol', 'amount',  'total_share', 'float_share',
            'pe', 'industry', 'area', 'float_mv', 'total_mv'
        ]
        existing_fields = [field for field in fields_to_keep if field in df_daily.columns]
        df_daily = df_daily[existing_fields]
        
        # 2. 下载资金流向数据 (按天循环)
        logging.info("正在下载资金流向数据...")
        df_moneyflow = download_data_in_date_range(pro.moneyflow, 'moneyflow', start_date, end_date)
        
        # 3. 过滤出需要处理的股票
        logging.info("按股票代码列表过滤日线数据...")
        df_daily_filtered = df_daily[df_daily['ts_code'].isin(stock_codes)]
        
        if df_daily_filtered.empty:
            logging.warning("根据股票代码列表，在下载的日线数据中未找到任何匹配项。")
            return

        df_integrated = df_daily_filtered
        # 4. 合并数据
        if not df_moneyflow.empty:
            logging.info("正在合并日线和资金流向数据...")
            # 使用 'ts_code' 和 'trade_date' 作为复合键进行左连接
            df_integrated = pd.merge(
                df_daily_filtered, 
                df_moneyflow, 
                on=["ts_code", "trade_date"], 
                how="left"
            )
            
            # 5. 添加主力净量字段
            logging.info("正在计算主力净量...")
            # 填充NaN值为0，以避免计算错误
            df_integrated['buy_lg_vol'] = df_integrated['buy_lg_vol'].fillna(0)
            df_integrated['sell_lg_vol'] = df_integrated['sell_lg_vol'].fillna(0)
            df_integrated['buy_elg_vol'] = df_integrated['buy_elg_vol'].fillna(0)
            df_integrated['sell_elg_vol'] = df_integrated['sell_elg_vol'].fillna(0)
            
            df_integrated['主力净量'] = (
                df_integrated['buy_lg_vol'] - df_integrated['sell_lg_vol'] +
                df_integrated['buy_elg_vol'] - df_integrated['sell_elg_vol']
            )

            # 添加"主力净量率"字段
            logging.info("正在计算主力净量率...")
            df_integrated['vol'] = df_integrated['vol'].fillna(0)
            df_integrated['主力净量率'] = np.where(
                df_integrated['vol'] > 0, 
                df_integrated['主力净量'] / df_integrated['vol'], 
                0
            )

            # 只保留日线字段和计算出的新字段
            final_columns = df_daily_filtered.columns.tolist() + ['主力净量', '主力净量率']
            df_integrated = df_integrated[final_columns]
        else:
            logging.warning("未下载到资金流向数据，仅处理日线数据。")
            df_integrated['主力净量'] = np.nan # 添加占位符列
            df_integrated['主力净量率'] = np.nan # 添加占位符列

        # 6. 保存为单个文件（改为写入MySQL）
        # 智能追加写入MySQL
        engine = db_utils.get_engine()
        try:
            existing = pd.read_sql('SELECT ts_code, trade_date FROM stock_daily', con=engine)
        except Exception:
            existing = pd.DataFrame(columns=['ts_code', 'trade_date'])  # 表不存在时
        merge_keys = ['ts_code', 'trade_date']
        merged = df_integrated.merge(existing, on=merge_keys, how='left', indicator=True)
        new_rows = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])
        if not new_rows.empty:
            new_rows.to_sql('stock_daily', con=engine, if_exists='append', index=False, chunksize=1000)
            logging.info(f'追加新数据 {len(new_rows)} 条到 stock_daily')
        else:
            logging.info('没有新数据需要追加。')
        
    except Exception as e:
        logging.error(f"处理股票数据时出错: {str(e)}")
        raise

def main():
    """主函数"""
    try:
        logging.info("=== 阶段1: 获取所有股票代码 ===")
        stock_codes = get_all_stock_codes()   
        if not stock_codes:
            logging.error("未获取到股票代码，程序终止")
            return

        # 设置保存目录
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(cur_dir, "stock_data")
        clear_folder(output_dir)

        logging.info("=== 阶段2: 下载并处理股票数据 ===")
        process_stock_data(stock_codes, output_dir)

        logging.info(f"=== 下载完成 ===")
        logging.info(f"总数: {len(stock_codes)}")
    except Exception as e:
        logging.error(f"程序运行出错: {e}")
        raise

if __name__ == "__main__":
    main()

