import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import random
from db_utils import get_dataframe

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
        
        # 设置样本数量
        self.sample_size = 100  # 总样本数量
        
        # 设置行业权重
        self.industry_weights = {
            '化学制药': 0.05, '生物制药': 0.03, '中成药': 0.03, '医疗保健': 0.04,
            '医药商业': 0.02, '元器件': 0.08, '半导体': 0.04, 'IT设备': 0.03,
            '通信设备': 0.05, '软件服务': 0.08, '互联网': 0.04, '家用电器': 0.05,
            '食品': 0.04, '白酒': 0.02, '啤酒': 0.01, '服饰': 0.03,
            '家居用品': 0.03, '汽车配件': 0.06, '汽车整车': 0.02, '其他': 0.30
        }
    
    def get_stock_basic_info(self):
        """从 bak_daily 表获取股票代码和市值信息，用于筛选"""
        try:
            # 从 bak_daily 表获取股票代码和市值信息（只选择00、30、60开头的股票）
            query = """
                SELECT DISTINCT 
                    ts_code,
                    float_mv
                FROM bak_daily 
                WHERE ts_code IS NOT NULL
                AND ts_code != ''
                AND float_mv IS NOT NULL
                AND float_mv > 0
                AND (ts_code LIKE %s OR ts_code LIKE %s OR ts_code LIKE %s)
            """
            
            # 使用参数化查询避免SQL注入和格式错误
            params = ('00%', '30%', '60%')
            
            df = get_dataframe(query, params=params)
            logging.info(f"成功从 bak_daily 表获取 {len(df)} 只股票代码。")
            
            if df.empty:
                raise Exception("未找到任何股票代码")
            
            # 筛选流通市值小于1000亿的股票（float_mv 单位是亿元）
            market_cap_limit = 1000  # 1000亿
            df_filtered = df[df['float_mv'] <= market_cap_limit].copy()
            logging.info(f"筛选流通市值小于 {market_cap_limit}亿 的股票后，剩余 {len(df_filtered)} 只。")
            
            # 根据股票代码分配行业（简化版本）
            def assign_industry(ts_code):
                """根据股票代码分配行业"""
                # 这里可以根据实际需要调整行业分配逻辑
                # 暂时使用简单的随机分配
                import random
                industries = list(self.industry_weights.keys())
                return random.choice(industries)
            
            df_filtered['industry'] = df_filtered['ts_code'].apply(assign_industry)
            
            # 输出统计信息
            logging.info(f"\n符合条件的股票数量: {len(df_filtered)} 只")
            
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
                # 随机选择
                selected = industry_stocks.sample(n=selected_count, random_state=42)
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
            
            logging.info(f"样本选择完成，共选择 {len(selected_stocks)} 只股票。")
            
            return selected_stocks
            
        except Exception as e:
            logging.error(f"选择样本股票失败: {str(e)}")
            return None
    
    def generate_sample_files(self, selected_stocks):
        """根据选择的股票代码，从 stock_daily_processed 表提取数据并生成样本文件"""
        try:
            # 从 stock_daily_processed 表获取样本股票的处理后数据
            placeholders = ','.join(['%s'] * len(selected_stocks))
            query = f"""
                SELECT *
                FROM stock_daily_processed 
                WHERE ts_code IN ({placeholders})
                ORDER BY ts_code, trade_date
            """
            
            # 将股票代码列表转换为元组
            stock_codes_tuple = tuple(selected_stocks)
            logging.info(f"正在查询 {len(selected_stocks)} 只股票的数据...")
            sample_df = get_dataframe(query, params=stock_codes_tuple)
            
            if sample_df.empty:
                logging.warning("未找到样本股票的处理后数据")
                return
            
            # 定义输出文件路径
            output_file = os.path.join(self.output_dir, 'sample_stocks_data.csv')
            
            logging.info(f"开始将 {len(selected_stocks)} 只样本股票的处理后数据保存到: {output_file}")
            logging.info(f"查询到的数据行数: {len(sample_df)}")
            sample_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            logging.info(f"样本数据文件已生成: {output_file}")
            logging.info(f"共保存 {len(sample_df)} 条记录")
            logging.info(f"数据列数: {len(sample_df.columns)}")
            logging.info(f"数据列名: {list(sample_df.columns)}")
            
        except Exception as e:
            logging.error(f"生成样本文件失败: {str(e)}")
            import traceback
            logging.error(f"详细错误信息: {traceback.format_exc()}")

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