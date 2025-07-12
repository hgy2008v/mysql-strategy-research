import os
import logging
import pandas as pd
import db_utils

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Config:
    """集中管理所有参数的配置类"""
    # 文件夹路径配置
    INPUT_DIR = 'stock_data'
    OUTPUT_DIR = 'test'
    EXCEL_FOLDER = 'other_data'
    
    # 输入文件
    PROCESSED_FILE = 'all_stocks_processed.csv'
    EXCEL_FILE = 'Table.xlsx'
    
    # 输出文件
    RANDOM_SAMPLE_FILE = 'random_sample_stocks.csv'
    EXCEL_SAMPLE_FILE = 'excel_sample_stocks.csv'
    
    # 抽样配置
    DEFAULT_SAMPLE_SIZE = 100  # 默认随机选择的股票数量

    # Excel读取配置
    STOCK_CODE_COLUMN = '代码'  # Excel中股票代码列名
    MARKET_CODES = {
        'SZ': '.SZ',
        'SH': '.SH'
    }

def read_stock_list_from_excel():
    """从Excel文件读取股票清单"""
    try:
        excel_path = os.path.join(Config.EXCEL_FOLDER, Config.EXCEL_FILE)
        if not os.path.exists(excel_path):
            logging.info(f"Excel文件不存在: {excel_path}。将使用随机抽样。")
            return None
            
        logging.info(f"尝试从Excel文件 {excel_path} 读取股票列表...")
        df = pd.read_excel(excel_path)
        
        if Config.STOCK_CODE_COLUMN not in df.columns:
            logging.error(f"Excel文件中未找到'{Config.STOCK_CODE_COLUMN}'列。")
            return None
        
        stock_list = []
        # 将代码列强制转换为字符串以处理数字格式
        for code in df[Config.STOCK_CODE_COLUMN].astype(str):
            code = code.strip().upper()
            if len(code) > 2:
                market = code[:2]
                number = code[2:]
                
                # 假设格式是 "SH600000" 或 "SZ000001"
                if market in Config.MARKET_CODES:
                    formatted_code = f"{number}{Config.MARKET_CODES[market]}"
                    stock_list.append(formatted_code)

        if not stock_list:
            logging.warning("未能从Excel中获取到格式正确 (如 SH600000) 的股票代码。")
            return None
            
        logging.info(f"成功从Excel读取 {len(stock_list)} 只股票。")
        return list(set(stock_list)) # 使用set去除重复项
        
    except Exception as e:
        logging.error(f"读取Excel文件时出错: {str(e)}")
        return None

def select_samples(input_dir, output_dir, stock_codes=None, sample_size=Config.DEFAULT_SAMPLE_SIZE):
    """
    从处理后的数据文件中选择股票样本。
    如果提供了stock_codes，则选择指定的股票。
    否则，随机选择指定数量的股票。
    """
    try:
        # 确保并清空输出目录
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"正在清空输出目录: {output_dir}...")
        for filename in os.listdir(output_dir):
            file_path = os.path.join(output_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logging.error(f"删除文件 {file_path} 失败: {e}")

        # 构造输入文件路径
        input_file_path = os.path.join(input_dir, Config.PROCESSED_FILE)
        if not os.path.exists(input_file_path):
            logging.error(f"输入文件未找到: {input_file_path}")
            return

        logging.info(f"开始从MySQL表 stock_processed 读取数据...")
        engine = db_utils.get_engine()
        df = pd.read_sql('SELECT * FROM stock_processed', con=engine)
        logging.info("数据读取完毕。")
        
        output_filename = ""
        selected_codes = []

        if stock_codes:
            # --- 按指定列表选择 ---
            logging.info(f"将根据Excel提供的列表选择 {len(stock_codes)} 只股票。")
            selected_codes = stock_codes
            output_filename = Config.EXCEL_SAMPLE_FILE
        else:
            # --- 随机选择 ---
            logging.info(f"将随机选择 {sample_size} 只股票。")
            all_stock_codes = df['ts_code'].unique()
            
            if len(all_stock_codes) < sample_size:
                logging.warning(f"请求的样本数量 {sample_size} 大于可用股票数量 {len(all_stock_codes)}。将使用所有可用股票。")
                sample_size = len(all_stock_codes)
            
            if sample_size > 0:
                selected_codes = pd.Series(all_stock_codes).sample(n=sample_size, random_state=42).tolist()
            output_filename = Config.RANDOM_SAMPLE_FILE

        if not selected_codes:
            logging.error("没有要抽样的股票代码，流程终止。")
            return

        logging.info(f"最终选择 {len(selected_codes)} 只股票进行抽样。")
        
        # 筛选出这些股票的所有历史数据
        sample_df = df[df['ts_code'].isin(selected_codes)]
        
        # 检查找到了多少只股票的数据
        found_codes = sample_df['ts_code'].unique()
        if len(found_codes) < len(selected_codes):
            missing_codes = set(selected_codes) - set(found_codes)
            logging.warning(f"在主数据文件中未找到以下 {len(missing_codes)} 只股票的数据: {', '.join(missing_codes)}")

        if sample_df.empty:
            logging.error("未能找到任何指定股票的数据，不生成样本文件。")
            return

        # 构造输出文件路径并保存
        output_file_path = os.path.join(output_dir, output_filename)
        sample_df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
        
        logging.info(f"样本数据已保存到: {output_file_path}")
        logging.info(f"样本文件包含 {len(sample_df)} 条记录，涉及 {len(found_codes)} 只股票。")

    except Exception as e:
        logging.error(f"抽样过程中发生错误: {str(e)}")
        raise

def main():
    """主函数"""
    logging.info("=== 开始数据样本选择流程 ===")
    
    # 首先尝试从Excel读取股票列表
    excel_stocks = read_stock_list_from_excel()
    
    # 执行抽样
    select_samples(
        input_dir=Config.INPUT_DIR,
        output_dir=Config.OUTPUT_DIR,
        stock_codes=excel_stocks, # 如果为None，则会进行随机抽样
        sample_size=Config.DEFAULT_SAMPLE_SIZE
    )
    
    logging.info("=== 数据样本选择流程结束 ===")

if __name__ == "__main__":
    main()