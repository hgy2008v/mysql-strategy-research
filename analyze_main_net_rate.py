import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm

def analyze_main_net_rate(file_path):
    """分析主力净量率与涨停概率的关系
    
    Args:
        file_path: 股票数据文件路径
    """
    print("正在读取数据...")
    # 读取数据
    df = pd.read_csv(file_path)
    
    # 确保数据包含必要的列
    required_columns = ['主力净量率', 'pct_chg', 'trade_date', 'open', 'close', 'ts_code']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"输入数据缺少必要的列: {', '.join(missing_columns)}")
    
    print("正在处理数据...")
    # 转换日期格式
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    
    # 计算第2、3、5天的收盘涨幅
    df['next_close_2'] = df.groupby('ts_code')['close'].shift(-1)
    df['next_close_3'] = df.groupby('ts_code')['close'].shift(-2)
    df['next_close_5'] = df.groupby('ts_code')['close'].shift(-4)
    
    df['next_pct_chg_2'] = (df['next_close_2'] / df['close'] - 1) * 100
    df['next_pct_chg_3'] = (df['next_close_3'] / df['close'] - 1) * 100
    df['next_pct_chg_5'] = (df['next_close_5'] / df['close'] - 1) * 100
    
    # 计算第2天的开盘和收盘涨停
    df['next_open'] = df.groupby('ts_code')['open'].shift(-1)
    df['next_close'] = df.groupby('ts_code')['close'].shift(-1)
    df['next_open_limit_up'] = (df['next_open'] / df['close'] - 1) >= 0.095
    df['next_close_limit_up'] = (df['next_close'] / df['close'] - 1) >= 0.095
    
    # 定义主力净量率区间
    rate_ranges = [
        (float('inf'), 0.3, '>0.3'),
        (0.3, 0.25, '0.25-0.3'),
        (0.25, 0.2, '0.2-0.25'),
        (0.2, 0.15, '0.15-0.2'),
        (0.15, 0.1, '0.1-0.15'),
        (0.1, 0.05, '0.05-0.1'),
        (0.05, float('-inf'), '<0.05')
    ]
    
    # 创建结果存储字典
    results = {
        'rate_range': [],
        'total_count': [],
        'limit_up_count': [],
        'limit_up_prob': [],
        'avg_pct_chg': [],
        'next_open_limit_up_count': [],
        'next_open_limit_up_prob': [],
        'next_close_limit_up_count': [],
        'next_close_limit_up_prob': [],
        'avg_pct_chg_2': [],
        'avg_pct_chg_3': [],
        'avg_pct_chg_5': []
    }
    
    print("正在分析各区间数据...")
    # 分析每个区间
    for upper, lower, range_name in tqdm(rate_ranges, desc="分析进度"):
        # 筛选区间内的数据
        if upper == float('inf'):
            mask = df['主力净量率'] > lower
        elif lower == float('-inf'):
            mask = df['主力净量率'] <= upper
        else:
            mask = (df['主力净量率'] <= upper) & (df['主力净量率'] > lower)
        
        range_data = df[mask]
        
        # 计算统计数据
        total_count = len(range_data)
        limit_up_count = len(range_data[range_data['pct_chg'] >= 9.5])  # 涨停阈值设为9.5%
        limit_up_prob = limit_up_count / total_count if total_count > 0 else 0
        avg_pct_chg = range_data['pct_chg'].mean()
        
        # 计算第2天开盘和收盘涨停
        next_open_limit_up_count = range_data['next_open_limit_up'].sum()
        next_open_limit_up_prob = next_open_limit_up_count / total_count if total_count > 0 else 0
        next_close_limit_up_count = range_data['next_close_limit_up'].sum()
        next_close_limit_up_prob = next_close_limit_up_count / total_count if total_count > 0 else 0
        
        # 计算第2、3、5天的平均收盘涨幅
        avg_pct_chg_2 = range_data['next_pct_chg_2'].mean()
        avg_pct_chg_3 = range_data['next_pct_chg_3'].mean()
        avg_pct_chg_5 = range_data['next_pct_chg_5'].mean()
        
        # 存储结果
        results['rate_range'].append(range_name)
        results['total_count'].append(total_count)
        results['limit_up_count'].append(limit_up_count)
        results['limit_up_prob'].append(limit_up_prob)
        results['avg_pct_chg'].append(avg_pct_chg)
        results['next_open_limit_up_count'].append(next_open_limit_up_count)
        results['next_open_limit_up_prob'].append(next_open_limit_up_prob)
        results['next_close_limit_up_count'].append(next_close_limit_up_count)
        results['next_close_limit_up_prob'].append(next_close_limit_up_prob)
        results['avg_pct_chg_2'].append(avg_pct_chg_2)
        results['avg_pct_chg_3'].append(avg_pct_chg_3)
        results['avg_pct_chg_5'].append(avg_pct_chg_5)
    
    # 创建结果DataFrame
    result_df = pd.DataFrame(results)
    
    print("\n正在计算相关系数...")
    # 计算相关系数
    correlation = df['主力净量率'].corr(df['pct_chg'])
    
    print("正在计算年度相关系数...")
    # 按年份分析
    df['year'] = df['trade_date'].dt.year
    yearly_analysis = df.groupby('year').apply(lambda x: x['主力净量率'].corr(x['pct_chg']))
    
    # 打印分析结果
    print("\n主力净量率与涨停概率分析结果：")
    print("="*80)
    print(result_df.to_string(index=False))
    
    print(f"\n主力净量率与涨跌幅的相关系数: {correlation:.4f}")
    
    print("\n分年度相关系数：")
    print(yearly_analysis)

if __name__ == "__main__":
    file_path = "merged_stock_data.csv"
    try:
        analyze_main_net_rate(file_path)
    except Exception as e:
        print(f"分析过程中发生错误: {str(e)}") 