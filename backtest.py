import os
import pandas as pd
import logging
import numpy as np
from tqdm import tqdm  # 添加tqdm库
import db_utils

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class StrategyConfig:
    """策略参数配置"""
    def __init__(self, params=None):
        """初始化策略配置
        
        Args:
            params (dict): 策略参数字典，如果为None则使用默认参数
        """
        # 默认参数
        self.INITIAL_AMOUNT = 10000
        self.MIN_HOLD_DAYS = 2
        self.VSHAPE_PREV_PRICE_POSITION = 0.17
        self.VSHAPE_PCT_CHG_MIN = 0.0  # 新增：V型转折公共涨幅参数
        self.VSHAPE_CONDITIONS = [
            {'min_slope': -0.01, 'max_slope': -0.0006, 'prev_rsd': 6.5},
            {'min_slope': -0.05, 'max_slope': -0.01, 'prev_rsd': 7.5},
            {'min_slope': -0.11, 'max_slope': -0.05, 'prev_rsd': 8.0},
            {'min_slope': -0.14, 'max_slope': -0.11, 'prev_rsd': 10.0},
            {'min_slope': -0.18, 'max_slope': -0.14, 'prev_rsd': 12.0},
            {'min_slope': -0.28, 'max_slope': -0.18, 'prev_rsd': 15.5},
            {'min_slope': -0.28, 'max_slope': float('inf'), 'prev_rsd': 20}
        ]
        self.BUY_CONDITIONS = {
            'CONDITION1': {
                'MAIN_NET_RATE_MIN': 0.2,
                'PREV_PRICE_POSITION_MAX': 1.0
            },
            'CONDITION4': {
                'CLOSE_SLOPE_MIN': 0.08,
                'PREV_RSD_MAX': 5.0,
                'RSD_CHG_MIN': 0.20
            }
        }
        self.SELL_CONDITIONS = [
            {'RSD_MIN': 2.5, 'RSD_MAX': 6.5, 'PRICE_TO_LOW_MIN': 1.3},
            {'RSD_MIN': 6.5, 'RSD_MAX': 11.5, 'PRICE_TO_LOW_MIN': 1.5},
            {'RSD_MIN': 11.5, 'RSD_MAX': 15.5, 'PRICE_TO_LOW_MIN': 1.8},
            {'RSD_MIN': 15.5, 'RSD_MAX': 20.0, 'PRICE_TO_LOW_MIN': 2.0},
            {'RSD_MIN': 20.0, 'RSD_MAX': 25.0, 'PRICE_TO_LOW_MIN': 2.2},
            {'RSD_MIN': 25, 'RSD_MAX': 30, 'PRICE_TO_LOW_MIN': 2.3},
            {'RSD_MIN': 30, 'RSD_MAX': float('inf'), 'PRICE_TO_LOW_MIN': 2.5}
        ]
        self.SELL_COMMON_CONDITIONS = {
            'PRICE_POSITION_CROSS': -1,
            'PRICE_POSITION_MIN': 0.80
        }
        
        # 如果提供了参数，则更新配置
        if params:
            self.update_params(params)
    
    def update_params(self, params):
        """更新策略参数
        
        Args:
            params (dict): 新的参数字典
        """
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logging.warning(f"未知参数: {key}")

# 创建默认配置实例
default_config = StrategyConfig()

def backtest_strategy(df, stock_code, config=None):
    """回测策略，返回交易记录
    
    Args:
        df (pd.DataFrame): 单只股票的数据
        stock_code (str): 股票代码
        config: 策略配置对象，如果为None则使用默认配置
        
    Returns:
        dict: 包含交易次数、胜率、总收益等信息的字典
    """
    # 使用提供的配置或默认配置
    strategy_config = config if config is not None else default_config
    
    try:
        # 数据已作为DataFrame传入，无需读取文件
        
        # 检查必要的列是否存在
        required_columns = ['trade_date', 'open', 'close', 'MA', 'MA_slope', 'Band_price_position', 'RSD', 'pct_chg', 
                           'Upper_Band', 'Lower_Band', 'price_position_cross', '90d_price_position',
                           'prev_Band_price_position', 'prev_90d_price_position']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"输入数据缺少必要的列: {', '.join(missing_columns)}")
        
        # 预处理数据
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y-%m-%d')
        df = df.sort_values('trade_date', ascending=True).reset_index(drop=True)
        
        # 数据完整性检查 - 静默处理缺失值
        if df.isnull().values.any():
            for col in df.columns[df.isna().any()].tolist():
                df[col] = df[col].ffill().bfill()
        
        # 添加回测所需的附加计算列
        df['next_open'] = df['open'].shift(-1)
        df['next_open'] = df['next_open'].ffill().bfill()
        
        # 初始化结果列
        df['信号'] = ''
        df['交易价格'] = 0.0
        df['买入数量'] = 0.0
        df['卖出数量'] = 0.0
        df['当次交易收益'] = 0.0
        df['当次交易收益率'] = 0.0
        df['累计收益'] = 0.0
        df['买卖原因'] = ''
        df['highest_price_updated'] = False  # 用于跟踪最高价更新点
        
        # 第一步：生成买入和卖出信号
        generate_buy_signals(df, strategy_config)
        generate_sell_signals(df, strategy_config)
        
        # 第二步：执行交易
        results, detailed_df = execute_trades(df, stock_code, strategy_config)
        
        return results, detailed_df
        
    except Exception as e:
        logging.error(f"回测股票 {stock_code} 过程中发生错误: {str(e)}")
        return {
            'trades': 0,
            'win_rate': 0,
            'total_profit': 0,
            'profit_rate': 0,
            'trade_records': pd.DataFrame(),
            'kelly_params': {
                'win_rate': 0,
                'odds': 0,
                'kelly_fraction': 0
            },
            'trade_stats': {
                'avg_win': 0,
                'avg_loss': 0,
                'max_drawdown': 0
            }
        }, pd.DataFrame()

def generate_buy_signals(df, config):
    """生成买入信号
    
    Args:
        df: 包含股票数据的DataFrame
        config: 策略配置对象
    """
    # 初始化买入相关列
    df['buy_condition'] = False
    df['buy_reason'] = ""
    
    # 添加调试信息
    buy_signals_count = 0
    
    # V型转折买入条件 - 暂时跳过，因为price_position_cross都是0
    # for i in range(len(df)):
    #     if df.at[i, 'price_position_cross'] == 1 and df.at[i, 'prev_Band_price_position'] <= config.VSHAPE_PREV_PRICE_POSITION:
    #         ma_slope = df.at[i, 'MA_slope']
    #         prev_rsd = df.at[i, 'prev_RSD']
    #         
    #         # 检查是否满足任一V型转折条件
    #         for idx, condition in enumerate(config.VSHAPE_CONDITIONS, 1):
    #             if (condition['min_slope'] <= ma_slope <= condition['max_slope'] and 
    #                 prev_rsd >= condition['prev_rsd'] and
    #                 df.at[i, 'pct_chg'] >= config.VSHAPE_PCT_CHG_MIN):
    #                 df.at[i, 'buy_condition'] = True
    #                 df.at[i, 'buy_reason'] = "V型转折+涨幅"
    #                 buy_signals_count += 1
    #                 break
    
    # 买入条件1：主力净量率和涨幅 - 放宽条件
    main_net_rate_condition = (
        (df['主力净量率'] >= 0.1) &  # 从0.2降低到0.1
        (df['prev_Band_price_position'] <= 1.0)
    )
    
    # 设置买入条件1
    df.loc[main_net_rate_condition & ~df['buy_condition'], 'buy_reason'] = "主力净量率+涨幅"
    df.loc[main_net_rate_condition, 'buy_condition'] = True
    buy_signals_count += len(df[main_net_rate_condition])

    
    # 买入条件4：横盘突破 - 放宽条件
    upper_trend_condition4 = (
        (df['CLOSE_slope'] > 0.05) &  # 从0.08降低到0.05
        (df['prev_RSD'] <= 8.0) &     # 从5.0提高到8.0
        (df['RSD_chg'] >= 0.10)       # 从0.20降低到0.10
    )
    
    # 设置买入条件4
    df.loc[upper_trend_condition4 & ~df['buy_condition'], 'buy_reason'] = "横盘突破"
    df.loc[upper_trend_condition4, 'buy_condition'] = True
    buy_signals_count += len(df[upper_trend_condition4])
    
    # 添加新的买入条件：简单的技术指标组合
    simple_buy_condition = (
        (df['pct_chg'] > 2.0) &           # 涨幅大于2%
        (df['主力净量率'] > 0.05) &        # 主力净量率大于0.05
        (df['RSD'] > 5.0) &               # RSD大于5
        (df['prev_Band_price_position'] < 0.8)  # 价格位置较低
    )
    
    df.loc[simple_buy_condition & ~df['buy_condition'], 'buy_reason'] = "简单技术组合"
    df.loc[simple_buy_condition, 'buy_condition'] = True
    buy_signals_count += len(df[simple_buy_condition])
    
    print(f"生成了 {buy_signals_count} 个买入信号")

def generate_sell_signals(df, config):
    """生成卖出信号
    
    Args:
        df: 包含股票数据的DataFrame
        config: 策略配置对象
    """
    # 初始化卖出相关列
    df['sell_condition'] = False
    df['sell_reason'] = ""
    
    # 添加调试信息
    sell_signals_count = 0
    
    # 简化的卖出条件：基于RSD和价格位置
    simple_sell_condition = (
        (df['RSD'] > 8.0) &                    # RSD大于8
        (df['Band_price_position'] > 0.7) &    # 价格位置较高
        (df['pct_chg'] < -1.0)                 # 当日跌幅大于1%
    )
    
    df.loc[simple_sell_condition, 'sell_condition'] = True
    df.loc[simple_sell_condition, 'sell_reason'] = "简化卖出条件"
    sell_signals_count += len(df[simple_sell_condition])
    
    # 添加止损条件：持仓时间过长
    # 这个条件在交易执行时处理
    
    # 添加止盈条件：涨幅过大
    profit_take_condition = (
        (df['pct_chg'] > 5.0) &                # 单日涨幅大于5%
        (df['RSD'] > 10.0)                     # RSD较高
    )
    
    df.loc[profit_take_condition & ~df['sell_condition'], 'sell_condition'] = True
    df.loc[profit_take_condition & ~df['sell_condition'], 'sell_reason'] = "止盈条件"
    sell_signals_count += len(df[profit_take_condition & ~df['sell_condition']])
    
    print(f"生成了 {sell_signals_count} 个卖出信号")

def execute_trades(df, stock_code, config):
    """执行交易逻辑
    
    Args:
        df: 包含股票数据和信号的DataFrame
        stock_code: 股票代码
        config: 策略配置对象
        
    Returns:
        dict: 包含交易统计信息的字典
    """
    # 初始化交易相关变量
    initial_amount = config.INITIAL_AMOUNT
    cash = float(initial_amount)
    position = 0.0
    trades = 0
    profits = []
    buy_price = 0.0
    buy_date = 0
    highest_price = 0.0
    
    # 初始化回测数据列
    df['现金余额'] = cash
    df['资产余额'] = 0.0
    df['持仓数量'] = 0.0
    df['持仓价值'] = 0.0
    df['price_drop'] = np.nan
    df['max_profit'] = np.nan

    # 执行交易逻辑
    for i in range(len(df)):
        # 继承前一天的数据
        if i > 0:
            df.at[i, '现金余额'] = df.at[i-1, '现金余额']
            df.at[i, '资产余额'] = df.at[i-1, '资产余额']
            df.at[i, '累计收益'] = df.at[i-1, '累计收益']
            df.at[i, '持仓数量'] = df.at[i-1, '持仓数量']
        
        # 更新当前持仓
        position = df.at[i, '持仓数量']
        cash = df.at[i, '现金余额']
        
        # 更新资产余额
        df.at[i, '持仓价值'] = position * df['close'][i]
        df.at[i, '资产余额'] = cash + df.at[i, '持仓价值']
        
        # 处理买入信号
        if position == 0 and df.at[i, 'buy_condition']:
            buy_price = df['next_open'][i]

            # 增加对买入价格的校验，防止为0或NaN
            if pd.isna(buy_price) or buy_price <= 0:
                continue  # 如果价格无效，则跳过此次交易

            buy_quantity = cash / buy_price
            position = buy_quantity
            cash = 0.0
            trades += 1
            buy_date = i
            highest_price = buy_price
            
            # 更新交易记录
            df.at[i, '信号'] = '买入'
            df.at[i, '交易价格'] = buy_price
            df.at[i, '买入数量'] = buy_quantity
            df.at[i, '持仓数量'] = position
            df.at[i, '现金余额'] = cash
            df.at[i, '买卖原因'] = df.at[i, 'buy_reason']
        
        # 处理持仓中的卖出逻辑
        elif position > 0:
            current_price = df['close'][i]
            days_held = i - buy_date
            
            # 更新最高价
            current_day_high = df['high'][i] if 'high' in df.columns else current_price
            
            if i > 0 and position > 0:
                previous_close = df['close'][i-1]
                current_open = df['open'][i]
                if current_open > previous_close:
                    true_high = max(current_day_high, current_open)
                else:
                    true_high = current_day_high
            else:
                true_high = current_day_high
            
            if true_high > highest_price:
                highest_price = true_high
                df.at[i, 'highest_price_updated'] = True
            else:
                df.at[i, 'highest_price_updated'] = False
            
            # 计算当前收益和回撤
            price_change = (current_price - buy_price) / buy_price
            df.at[i, 'price_drop'] = price_change
            
            max_profit = (highest_price - buy_price) / buy_price
            df.at[i, 'max_profit'] = max_profit
            
            # 初始化卖出条件
            sell_condition = False
            sell_reason = ""
            
            # 1. 最小持仓期保护
            if days_held >= config.MIN_HOLD_DAYS:
                # 2. 检查策略卖出信号
                if df.at[i, 'sell_condition']:
                    sell_condition = True
                    sell_reason = df.at[i, 'sell_reason']
            
            # 执行卖出
            if sell_condition:
                sell_price = df['next_open'][i]

                # 增加对卖出价格的校验
                if pd.isna(sell_price) or sell_price < 0:
                    continue # 如果价格无效，则跳过

                sell_quantity = position
                cash += sell_quantity * sell_price
                current_profit = sell_quantity * (sell_price - buy_price)

                # 增加对买入价格的校验，避免除以0
                if buy_price > 0:
                    current_return = (sell_price - buy_price) / buy_price
                else:
                    current_return = 0.0
                
                profits.append(current_profit)
                position = 0.0
                
                # 更新交易记录
                df.at[i, '信号'] = '卖出'
                df.at[i, '交易价格'] = sell_price
                df.at[i, '卖出数量'] = sell_quantity
                df.at[i, '当次交易收益'] = current_profit
                df.at[i, '当次交易收益率'] = current_return
                df.at[i, '累计收益'] += current_profit
                df.at[i, '持仓数量'] = 0.0
                df.at[i, '现金余额'] = cash
                df.at[i, '买卖原因'] = sell_reason

    # 计算回测结果
    total_profit = sum(p for p in profits if pd.notnull(p)) if profits else 0
    win_rate = sum(1 for p in profits if p > 0) / len(profits) if profits else 0
    final_value = cash + (position * df['close'].iloc[-1]) if position > 0 else cash
    total_return = (total_profit / initial_amount) * 100

    # 计算凯利公式参数
    kelly_win_rate, kelly_odds = calculate_kelly_parameters(profits)
    kelly_fraction = calculate_kelly_fraction(kelly_win_rate, kelly_odds)

    # 交易记录
    trade_df = df[df['信号'].isin(['买入', '卖出'])][['trade_date', '信号', '交易价格', '买入数量', '卖出数量', '当次交易收益', '当次交易收益率', '买卖原因']]

    results_dict = {
        'trades': trades,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'profit_rate': total_return,
        'trade_records': trade_df,
        'kelly_params': {
            'win_rate': kelly_win_rate,
            'odds': kelly_odds,
            'kelly_fraction': kelly_fraction
        },
        'trade_stats': {
            'avg_win': kelly_win_rate,
            'avg_loss': kelly_odds,
            'max_drawdown': calculate_max_drawdown(profits)
        }
    }
    return results_dict, df

def calculate_max_drawdown(profits):
    """计算最大回撤率
    
    Args:
        profits: 交易收益列表
        
    Returns:
        float: 最大回撤率
    """
    if not profits:
        return 0
        
    max_drawdown = 0
    peak = profits[0]
    for p in profits:
        if pd.notnull(p):
            if p > peak:
                peak = p
            drawdown = (peak - p) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown

def calculate_kelly_parameters(profits):
    """计算凯利公式所需参数
    
    Args:
        profits: 交易收益列表
        
    Returns:
        tuple: (胜率, 赔率)
    """
    if not profits:
        return 0, 0
        
    # 计算胜率
    win_rate = sum(1 for p in profits if p > 0) / len(profits)
    
    # 计算平均盈利和平均亏损
    winning_trades = [p for p in profits if p > 0]
    losing_trades = [p for p in profits if p < 0]
    
    avg_win = np.mean(winning_trades) if winning_trades else 0
    avg_loss = abs(np.mean(losing_trades)) if losing_trades else 0
    
    # 计算赔率（修正）
    odds = avg_win / avg_loss if avg_loss != 0 else 0
    
    return win_rate, odds

def calculate_kelly_fraction(win_rate, odds):
    """计算凯利公式建议的仓位比例
    
    Args:
        win_rate: 胜率
        odds: 赔率
        
    Returns:
        float: 建议的仓位比例
    """
    if odds <= 0 or win_rate <= 0:
        return 0
        
    # 凯利公式：f = (bp - q) / b
    # 其中：f是仓位比例，b是赔率，p是胜率，q是失败率
    kelly_fraction = (odds * win_rate - (1 - win_rate)) / odds
    
    # 使用半凯利策略，并设置合理的上下限
    half_kelly = kelly_fraction / 2
    
    # 设置合理的仓位限制：最小0%，最大50%
    return max(0, min(0.5, half_kelly))

def print_backtest_results(all_results):
    """打印回测结果
    
    Args:
        all_results: 包含所有股票回测结果的列表
    """
    if not all_results:
        print("没有回测结果")
        return
        
    # 将结果转换为DataFrame
    df = pd.DataFrame(all_results)
    
    # 计算总体统计信息
    total_trades = df['交易次数'].sum()
    win_trades = int(df['胜率'].mean() * total_trades)
    loss_trades = total_trades - win_trades
    total_profit = df['总收益'].sum()
    avg_profit = df['总收益'].mean()
    max_profit = df['总收益'].max()
    min_profit = df['总收益'].min()
    avg_win_rate = df['胜率'].mean()
    
    # 打印总体统计信息
    print("\n" + "="*50)
    print("回测总体统计")
    print("="*50)
    print(f"总交易次数: {total_trades}")
    print(f"盈利次数: {win_trades}")
    print(f"亏损次数: {loss_trades}")
    print(f"平均胜率: {avg_win_rate:.2%}")
    print(f"总收益: {total_profit:,.2f}")
    print(f"平均收益: {avg_profit:,.2f}")
    print(f"最大收益: {max_profit:,.2f}")
    print(f"最小收益: {min_profit:,.2f}")
    
    # 打印个股详细结果
    print("\n" + "="*50)
    print("个股详细结果")
    print("="*50)
    
    # 设置显示选项
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.float_format', '{:,.2f}'.format)
    
    # 按总收益排序
    df = df.sort_values('总收益', ascending=False)
    
    # 打印前10只和后10只股票
    print("\n收益最高的10只股票:")
    print(df.head(10)[['股票代码', '交易次数', '胜率', '总收益', '收益率', '平均盈利', '平均亏损', '最大回撤']].to_string(index=False))
    
    print("\n收益最低的10只股票:")
    print(df.tail(10)[['股票代码', '交易次数', '胜率', '总收益', '收益率', '平均盈利', '平均亏损', '最大回撤']].to_string(index=False))
    
    # 打印收益分布
    print("\n" + "="*50)
    print("收益分布统计")
    print("="*50)
    print(df['总收益'].describe().to_string())
    
    # 打印胜率分布
    print("\n" + "="*50)
    print("胜率分布统计")
    print("="*50)
    print(df['胜率'].describe().to_string())
    
    # 重置显示选项
    pd.reset_option('display.max_columns')
    pd.reset_option('display.width')
    pd.reset_option('display.float_format')

def format_stock_result(result):
    """格式化单个股票的回测结果
    
    Args:
        result: 单个股票的回测结果字典
        
    Returns:
        str: 格式化后的结果字符串
    """
    return (
        f"股票代码: {result['股票代码']}\n"
        f"交易次数: {result['交易次数']}\n"
        f"胜率: {result['胜率']:.2%}\n"
        f"总收益: {result['总收益']:.2f}\n"
        f"收益率: {result['收益率']:.2f}%\n"
        f"平均盈利: {result['平均盈利']:.2f}\n"
        f"平均亏损: {result['平均亏损']:.2f}\n"
        f"最大回撤: {result['最大回撤']:.2f}\n"
        f"凯利胜率: {result['凯利胜率']:.2%}\n"
        f"凯利赔率: {result['凯利赔率']:.2f}\n"
        f"建议仓位: {result['建议仓位']:.2%}\n"
        f"{'-'*50}"
    )

def main(data_file_path):
    """主函数，执行批量回测
    
    Args:
        data_file_path (str): 包含所有样本股票数据的单个文件路径
    """
    # 创建策略配置实例
    config = StrategyConfig()
    initial_amount = config.INITIAL_AMOUNT  # 初始资金

    logging.info(f"开始从CSV文件读取样本数据: {data_file_path}")
    try:
        all_stocks_df = pd.read_csv(data_file_path, encoding='utf-8-sig')
    except Exception as e:
        logging.error(f"读取CSV文件时出错: {e}")
        return
    logging.info(f"数据读取完毕，包含 {all_stocks_df['ts_code'].nunique()} 只股票，总行数: {len(all_stocks_df)}。")

    # 创建并清理输出目录
    output_dir = 'output/original'
    if os.path.exists(output_dir):
        # 删除目录中的所有文件
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                    print(f"已删除文件: {file_path}")
            except Exception as e:
                print(f"删除文件 {file_path} 时出错: {str(e)}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    print(f"输出目录已清理: {output_dir}")
    
    # 创建一个字典来存储每个股票代码的最新结果
    stock_results = {}
    
    # 创建一个DataFrame来存储所有股票的结果
    all_results = []
    all_details_dfs = [] # 用于存储所有详情DataFrame
    
    # 按股票代码分组
    grouped_stocks = all_stocks_df.groupby('ts_code')

    # 使用tqdm显示进度条
    print("\n开始批量回测...")
    for stock_code, stock_df in tqdm(grouped_stocks, desc="回测进度", unit="只"):
        try:
            # 传递单只股票的DataFrame进行回测
            results, detailed_df = backtest_strategy(stock_df.copy(), stock_code, config)
            
            # 将详情DataFrame添加到列表中
            if not detailed_df.empty:
                all_details_dfs.append(detailed_df)

            stock_results[stock_code] = results
            
            # 将结果添加到汇总列表
            result_dict = {
                '股票代码': stock_code,
                '交易次数': results['trades'],
                '胜率': results['win_rate'],
                '总收益': results['total_profit'],
                '收益率': results['profit_rate'],
                '平均盈利': results['trade_stats']['avg_win'],
                '平均亏损': results['trade_stats']['avg_loss'],
                '最大回撤': results['trade_stats']['max_drawdown'],
                '凯利胜率': results['kelly_params']['win_rate'],
                '凯利赔率': results['kelly_params']['odds'],
                '建议仓位': results['kelly_params']['kelly_fraction']
            }
            all_results.append(result_dict)
            
            # 打印当前股票的回测结果
            print(f"\n{format_stock_result(result_dict)}")
            
        except Exception as e:
            print(f"\n处理股票 {stock_code} 时出错: {str(e)}")
            continue
    
    # 保存汇总结果
    summary_df = pd.DataFrame(all_results)
    summary_file = os.path.join(output_dir, 'summary_results.csv')
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')
    print(f"\n已保存汇总结果到: {summary_file}")
    
    # 合并并保存所有详情数据
    if all_details_dfs:
        logging.info("正在合并所有回测详情到一个文件中...")
        full_details_df = pd.concat(all_details_dfs, ignore_index=True)
        details_file = os.path.join(output_dir, 'all_backtest_details.csv')
        full_details_df.to_csv(details_file, index=False, encoding='utf-8-sig')
        logging.info(f"所有回测详情已保存到: {details_file}")
    else:
        logging.warning("没有生成任何回测详情数据。")

    # 使用去重后的结果计算汇总统计
    unique_results = list(stock_results.values())
    
    # 计算并输出汇总结果
    total_trades = sum(r['trades'] for r in unique_results)
    total_profit = sum(r['total_profit'] for r in unique_results)
    initial_total_capital = initial_amount * len(unique_results)
    total_return = (total_profit / initial_total_capital) * 100
    avg_win_rate = sum(r['win_rate'] for r in unique_results) / len(unique_results) if unique_results else 0
    
    print("\n汇总结果:")
    print(f"测试股票数量: {len(unique_results)}")
    print(f"总交易次数: {total_trades}")
    print(f"平均胜率: {avg_win_rate:.2%}")
    print(f"总累计收益: {total_profit:.2f}")
    print(f"总累计收益率: {total_return:.2f}%")
    
    # 计算并输出汇总的凯利公式参数
    avg_kelly_win_rate = sum(r['kelly_params']['win_rate'] for r in unique_results) / len(unique_results)
    avg_kelly_odds = sum(r['kelly_params']['odds'] for r in unique_results) / len(unique_results)
    
    # 使用平均胜率和平均赔率计算凯利仓位
    avg_kelly_fraction = calculate_kelly_fraction(avg_kelly_win_rate, avg_kelly_odds)
    
    print("\n汇总凯利公式参数:")
    print(f"平均胜率: {avg_kelly_win_rate:.2%}")
    print(f"平均赔率: {avg_kelly_odds:.2f}")
    print(f"基于平均参数的建议仓位比例: {avg_kelly_fraction:.2%}")
    
    # 计算并输出基于交易次数的加权平均凯利仓位
    weighted_kelly_fraction = sum(r['kelly_params']['kelly_fraction'] * r['trades'] for r in unique_results) / total_trades if total_trades > 0 else 0
    print(f"基于交易次数加权的建议仓位比例: {weighted_kelly_fraction:.2%}")

    # 打印回测结果
    print_backtest_results(all_results)

if __name__ == "__main__":
    test_folder = 'test'
    stock_file_to_test = None
    
    # 定义可能的样本文件名，可以按优先级排序
    possible_files = ['sample_stocks_data.csv', 'random_sample_stocks.csv', 'excel_sample_stocks.csv']
    
    # 查找优先的样本文件
    for f_name in possible_files:
        path = os.path.join(test_folder, f_name)
        if os.path.exists(path):
            stock_file_to_test = path
            logging.info(f"找到样本文件进行回测: {stock_file_to_test}")
            break
            
    # 如果没有找到优先文件，则查找目录中任何其他CSV文件
    if not stock_file_to_test:
        try:
            all_csvs = [os.path.join(test_folder, f) for f in os.listdir(test_folder) if f.endswith('.csv')]
            if all_csvs:
                stock_file_to_test = all_csvs[0]
                logging.info(f"未找到特定样本文件，使用找到的第一个CSV进行回测: {stock_file_to_test}")
        except FileNotFoundError:
            pass # 目录可能不存在，下面会处理

    if not stock_file_to_test:
        raise FileNotFoundError(f"在 '{test_folder}' 文件夹中没有找到任何可用于回测的CSV样本文件。")
    
    main(stock_file_to_test)
