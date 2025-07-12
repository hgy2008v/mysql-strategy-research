import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import random
import db_utils

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StockSampleSelector:
    """股票样本选择器"""
    
    def __init__(self, input_dir='stock_data', output_dir='test'):
        """
        初始化样本选择器
        
        参数:
            input_dir (str): 包含处理后数据的目录
            output_dir (str): 输出样本的目录
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        
        # 创建并清空输出目录
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"正在清空输出目录: {self.output_dir}...")
        for filename in os.listdir(self.output_dir):
            file_path = os.path.join(self.output_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logging.error(f"删除文件 {file_path} 失败: {e}")

        # 设置样本数量
        self.sample_size = 100 # 总样本数量
        
        # 设置行业权重
        self.industry_weights = {
            '化学制药': 0.05, '生物制药': 0.03, '中成药': 0.03, '医疗保健': 0.04,
            '医药商业': 0.02, '元器件': 0.08, '半导体': 0.04, 'IT设备': 0.03,
            '通信设备': 0.05, '软件服务': 0.08, '互联网': 0.04, '家用电器': 0.05,
            '食品': 0.04, '白酒': 0.02, '啤酒': 0.01, '服饰': 0.03,
            '家居用品': 0.03, '汽车配件': 0.06, '汽车整车': 0.02, '其他': 0.30
        }
    
    def get_stock_basic_info(self):
        """从 latest_stock_data.csv 获取最新的股票基本信息，用于筛选"""
        try:
            logging.info(f"正在从MySQL表 stock_processed 读取股票基本信息...")
            engine = db_utils.get_engine()
            df = pd.read_sql('SELECT * FROM stock_processed', con=engine)
            logging.info(f"成功从MySQL表 stock_processed 读取 {len(df)} 条记录。")
            
            if 'float_mv' in df.columns:
                # 筛选流通市值小于1000亿的股票 (float_mv 单位: 万元)
                market_cap_limit = 10000000  # 1000亿 = 1000 * 10000 万元
                df_filtered = df[df['float_mv'] <= market_cap_limit].copy()
                logging.info(f"筛选流通市值小于 {market_cap_limit / 10000}亿 的股票后，剩余 {len(df_filtered)} 只。")
            else:
                logging.info("股票数据中没有 float_mv 列，无法进行市值筛选。")
            
            # 输出统计信息
            logging.info("\n符合条件的股票行业分布:")
            industry_dist = df_filtered['industry'].value_counts()
            for industry, count in industry_dist.items():
                logging.info(f"{industry}: {count}只")
            
            return df_filtered
            
        except Exception as e:
            logging.error(f"获取股票基本信息失败: {str(e)}")
            return None
    
    def select_stocks_by_industry(self, df, target_size):
        """按行业权重选择股票"""
        selected_stocks = []
        
        industry_targets = {industry: int(target_size * weight) for industry, weight in self.industry_weights.items()}
        
        for industry, target_count in industry_targets.items():
            industry_stocks = df[df['industry'] == industry]
            actual_count = len(industry_stocks)
            
            if actual_count > 0:
                selected_count = min(actual_count, target_count)
                # 按市值降序选择
                selected = industry_stocks.sort_values('float_mv', ascending=False).head(selected_count)
                selected_stocks.extend(selected['ts_code'].tolist())
        
        logging.info(f"\n总共选择了 {len(selected_stocks)} 只股票")
        return selected_stocks
    
    def select_sample_stocks(self):
        """选择样本股票"""
        try:
            df = self.get_stock_basic_info()
            if df is None or df.empty:
                logging.error("未能获取到股票基本信息，样本选择终止。")
                return None
            
            selected_stocks = self.select_stocks_by_industry(df, self.sample_size)
            
            selected_df = df[df['ts_code'].isin(selected_stocks)]
            selected_df.to_csv(os.path.join(self.output_dir, 'selected_stocks.csv'), index=False, encoding='utf-8-sig')
            
            logging.info(f"样本选择完成，共选择 {len(selected_stocks)} 只股票。最终行业分布:")
            industry_dist = selected_df['industry'].value_counts()
            for industry, count in industry_dist.items():
                logging.info(f"{industry}: {count}只")
            
            return selected_stocks
            
        except Exception as e:
            logging.error(f"选择样本股票失败: {str(e)}")
            return None
    
    def generate_sample_files(self, selected_stocks):
        """根据选择的股票代码，从主数据文件中提取数据并生成单个样本文件"""
        try:
            logging.info(f"正在从MySQL表 stock_processed 读取主数据以生成样本...")
            engine = db_utils.get_engine()
            main_df = pd.read_sql('SELECT * FROM stock_processed', con=engine)
            
            # 一次性筛选出所有样本股票的数据
            sample_df = main_df[main_df['ts_code'].isin(selected_stocks)]
            
            # 定义输出文件路径
            output_file = os.path.join(self.output_dir, 'sample_stocks_data.csv')
            
            logging.info(f"开始将 {len(selected_stocks)} 只样本股票的数据合并保存到: {output_file}")
            sample_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            logging.info(f"样本数据文件已生成: {output_file}")
            
        except Exception as e:
            logging.error(f"生成样本文件失败: {str(e)}")

def main():
    """主函数"""
    selector = StockSampleSelector(input_dir='stock_data', output_dir='test')
    
    selected_stocks = selector.select_sample_stocks()
    
    if selected_stocks:
        selector.generate_sample_files(selected_stocks)
    else:
        logging.error("样本选择失败，未生成样本文件。")

if __name__ == "__main__":
    main() 