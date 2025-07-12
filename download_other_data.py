import tushare as ts
import pandas as pd
import akshare as ak
import os
import logging
import datetime
import numpy as np
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
import db_utils
from sqlalchemy import text

# 初始化日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 全局变量
pro = None

def init_tushare():
    """初始化 Tushare API"""
    global pro
    if pro is None:
        ts.set_token('dd29d91ca9f8577814389ee9e722991fe05df214e1755d82702f956d')
        pro = ts.pro_api()
    return pro

# 初始化下载队列和结果队列
download_queue = queue.Queue()
result_queue = queue.Queue()

def process_download_queue(max_workers=5, max_retries=3):
    """处理下载队列中的任务"""
    def worker(task):
        for retry in range(max_retries):
            try:
                result = task['func'](task['date'])
                if isinstance(result, pd.DataFrame) and not result.empty:
                    result_queue.put(result)
                    return
            except Exception as e:
                logging.warning(f"下载{task['type']}数据失败 (尝试 {retry + 1}/{max_retries}): {str(e)}")
                time.sleep(1)  # 失败后等待1秒再重试
        return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        while not download_queue.empty():
            task = download_queue.get()
            executor.submit(worker, task)

def get_dates():
    """获取今天和昨天的日期"""
    today = datetime.datetime.now().strftime("%Y%m%d")
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y%m%d")
    return today, yesterday

def ensure_directory_exists(file_path):
    """确保目标目录存在"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

def download_data_with_retry(api_call, *args, retry_days=1, **kwargs):
    """通用数据下载函数，支持重试前几天的数据"""
    try:
        today, yesterday = get_dates()
        dates_to_try = [today] + [(datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y%m%d") 
                                 for i in range(1, retry_days + 1)]
        
        for date in dates_to_try:
            try:
                df = api_call(*args, **kwargs) if not kwargs.get('trade_date') else api_call(trade_date=date, *args, **kwargs)
                if not df.empty:
                    return df
            except Exception as e:
                logging.warning(f"尝试获取{date}数据失败: {str(e)}")
                continue
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"数据下载失败: {str(e)}")
        return pd.DataFrame()

def save_data_with_replace(df, table_name, engine):
    """使用REPLACE INTO保存数据，避免重复键错误"""
    if df.empty:
        return True
    
    try:
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
            
            logging.info(f"成功使用REPLACE INTO保存 {len(df)} 条数据到 {table_name}")
            return True
            
    except Exception as e:
        logging.error(f"保存数据到 {table_name} 失败: {str(e)}")
        return False

def save_data(df, filename, data_dir="other_data", add_timestamp=True):
    """通用数据保存函数，使用REPLACE INTO避免重复键错误"""
    try:
        if df.empty:
            logging.warning(f"数据为空，不保存 {filename}")
            return None
        if add_timestamp:
            df['获取数据时间'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        table_name = filename.replace('.csv', '').replace('.', '_')
        engine = db_utils.get_engine()
        
        # 使用自定义的REPLACE INTO方法
        if save_data_with_replace(df, table_name, engine):
            return table_name
        else:
            return None
    except Exception as e:
        logging.error(f"保存数据到MySQL失败: {str(e)}")
        return None

def download_market_margin():
    """下载全市场融资数据"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        df_sh = download_data_with_retry(pro.margin_secs, exchange='SSE')
        df_sz = download_data_with_retry(pro.margin_secs, exchange='SZSE')
        df_margin = pd.concat([df_sh, df_sz], axis=0)
        return save_data(df_margin, "merged_market_margin.csv")
    except Exception as e:
        logging.error(f"下载市场融资数据失败: {str(e)}")
        return None

def download_market_moneyflow():
    """下载大盘资金流向数据"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        today, yesterday = get_dates()
        start_date = (datetime.datetime.today() - datetime.timedelta(days=182)).strftime("%Y%m%d")
        
        market_moneyflow_df = download_data_with_retry(pro.moneyflow_mkt_dc, start_date=start_date, end_date=today)
        
        if not market_moneyflow_df.empty:
            market_moneyflow_df['total_amount'] = market_moneyflow_df['net_amount'] / (market_moneyflow_df['net_amount_rate'].replace(0, np.nan) / 100)
            market_moneyflow_df = market_moneyflow_df.sort_values('trade_date')
            market_moneyflow_df['环比增长率'] = market_moneyflow_df['total_amount'].pct_change().round(4)
            market_moneyflow_df.iloc[0, market_moneyflow_df.columns.get_loc('环比增长率')] = np.nan
            market_moneyflow_df['end_date'] = today

        return save_data(market_moneyflow_df, "market_moneyflow.csv")
    except Exception as e:
        logging.error(f"下载大盘资金流向数据失败: {str(e)}")
        return None

def download_sector_moneyflow():
    """下载板块资金流向数据"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        today = datetime.datetime.now().strftime("%Y%m%d")
        start_date = (datetime.datetime.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        
        # 获取板块资金流向数据
        sector_moneyflow_df = pro.moneyflow_ind_dc(start_date=start_date, end_date=today)
        
        if sector_moneyflow_df.empty:
            logging.info("板块资金流向数据为空。")
            return None

        # 数据处理
        sector_moneyflow_df = sector_moneyflow_df.sort_values('trade_date')
        sector_moneyflow_df['板块资金净流入环比'] = (sector_moneyflow_df['net_amount'].pct_change()).round(4)
        sector_moneyflow_df.iloc[0, sector_moneyflow_df.columns.get_loc('板块资金净流入环比')] = np.nan

        # 保存数据
        table_name = "sector_moneyflow"
        engine = db_utils.get_engine()
        sector_moneyflow_df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        logging.info(f"成功保存板块资金流向数据到MySQL表 {table_name}，数据量：{len(sector_moneyflow_df)} 行")
        return table_name
        
    except Exception as e:
        logging.error(f"下载板块资金流向数据失败，请检查: 1.Token有效性 2.网络连接 3.API权限\n错误详情: {str(e)}")
        return None

def download_other_data():
    """下载其他市场数据"""
    data_functions = [
        (ak.stock_board_change_em, "stock_board_change.csv"),
        (lambda: ak.stock_zt_pool_em(date=get_dates()[0]), "stock_zt_pool.csv"),
        (lambda: ak.stock_zt_pool_strong_em(date=get_dates()[0]), "stock_zt_pool_strong.csv"),
        (ak.stock_market_activity_legu, "stock_market_activity_legu.csv"),
        (ak.stock_zt_pool_zbgc_em, "stock_zt_pool_zbgc.csv"),
        (ak.stock_rank_cxfl_ths, "stock_rank_cxfl.csv"),
        (ak.stock_rank_cxsl_ths, "stock_rank_cxsl.csv"),
        (lambda: ak.stock_rank_xstp_ths(symbol="10日均线"), "stock_rank_xstp.csv"),
        (lambda: ak.stock_rank_xxtp_ths(symbol="10日均线"), "stock_rank_xxtp.csv"),
        (ak.stock_rank_ljqs_ths, "stock_rank_ljqs.csv"),
        (ak.stock_rank_ljqd_ths, "stock_rank_ljqd.csv")
    ]

    for func, filename in data_functions:
        try:
            df = download_data_with_retry(func)
            save_data(df, filename)
        except Exception as e:
            logging.error(f"下载 {filename} 数据失败: {str(e)}")

def get_concept_cons():
    """
    获取概念成分股
   """
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        # 使用 pro.kpl_concept_cons 获取概念成分股列表
        concept_cons = pro.kpl_concept_cons()
        
        # 保存到数据库而不是CSV文件
        return save_data(concept_cons, "concept_cons.csv")
              
    except Exception as e:
        logging.error(f"获取概念成分股失败: {e}")
        return None
    
def download_top_list():
    """下载龙虎榜数据"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        today, yesterday = get_dates()
        start_date = (datetime.datetime.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        df_top_list = []
        
        # 创建日期列表
        date_list = list(pd.date_range(start=start_date, end=today))
        
        # 将下载任务添加到队列
        for date in date_list:
            trade_date = date.strftime('%Y%m%d')
            download_queue.put({
                'type': 'top_list',
                'date': trade_date,
                'func': lambda d: pro.top_list(trade_date=d, tag='', fields='')
            })
        
        # 处理下载队列
        process_download_queue()
        
        # 收集结果
        while not result_queue.empty():
            result = result_queue.get()
            if isinstance(result, pd.DataFrame) and not result.empty:
                df_top_list.append(result)
        
        if df_top_list:
            final_df = pd.concat(df_top_list, ignore_index=True)
            return save_data(final_df, "top_list.csv")
        else:
            logging.warning("未获取到任何龙虎榜数据")
            return None
            
    except Exception as e:
        logging.error(f"下载龙虎榜数据失败: {str(e)}")
        return None

def download_top_inst():
    """下载机构交易数据"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        today, yesterday = get_dates()
        start_date = (datetime.datetime.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        df_top_inst_list = []
        
        # 创建日期列表
        date_list = list(pd.date_range(start=start_date, end=today))
        
        # 将下载任务添加到队列
        for date in date_list:
            trade_date = date.strftime('%Y%m%d')
            download_queue.put({
                'type': 'top_inst',
                'date': trade_date,
                'func': lambda d: pro.top_inst(trade_date=d, tag='', fields='')
            })
        
        # 处理下载队列
        process_download_queue()
        
        # 收集结果
        while not result_queue.empty():
            result = result_queue.get()
            if isinstance(result, pd.DataFrame) and not result.empty:
                df_top_inst_list.append(result)
        
        if df_top_inst_list:
            final_df = pd.concat(df_top_inst_list, ignore_index=True)
            return save_data(final_df, "top_inst.csv")
        else:
            logging.warning("未获取到任何机构交易数据")
            return None
            
    except Exception as e:
        logging.error(f"下载机构交易数据失败: {str(e)}")
        return None

def download_concept_data():
    """下载概念数据并计算连续上涨天数"""
    try:
        # 初始化 tushare
        pro = init_tushare()
        
        today, yesterday = get_dates()
        start_date = (datetime.datetime.today() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        df_list = []
        
        # 创建日期列表
        date_list = list(pd.date_range(start=start_date, end=today))
        
        # 将下载任务添加到队列
        for date in date_list:
            trade_date = date.strftime('%Y%m%d')
            download_queue.put({
                'type': 'concept_data',
                'date': trade_date,
                'func': lambda d: pro.kpl_concept(trade_date=d)
            })
        
        # 处理下载队列
        process_download_queue()
        
        # 收集结果
        while not result_queue.empty():
            result = result_queue.get()
            if isinstance(result, pd.DataFrame) and not result.empty:
                df_list.append(result)
        
        if df_list:
            # 合并数据并处理
            df = pd.concat(df_list, ignore_index=True)
            df = df.sort_values(['ts_code', 'trade_date'])
            
            # 计算连续上涨天数
            df['z_t_num_diff'] = df.groupby('ts_code')['z_t_num'].diff() > 0
            df['continuous_increase_days'] = df.groupby('ts_code')['z_t_num_diff'].apply(
                lambda x: x.groupby((~x).cumsum()).cumsum()
            ).reset_index(level=0, drop=True).astype(int)
            df = df.drop('z_t_num_diff', axis=1)
            
            # 保存数据
            return save_data(df, "concept_data.csv")
        else:
            logging.warning("未获取到任何概念数据")
            return None
            
    except Exception as e:
        logging.error(f"下载概念数据失败: {str(e)}")
        return None

def main():
    """主函数"""
    functions_to_run = [
        download_market_moneyflow,
        download_sector_moneyflow,
        download_top_list,
        download_top_inst,
        get_concept_cons,
        
        download_concept_data  # 添加新的下载函数
    ]

    for func in functions_to_run:
        try:
            func()
        except Exception as e:
            logging.error(f"执行 {func.__name__} 失败: {str(e)}")

if __name__ == "__main__":
    main() 
