import os
import pandas as pd
import numpy as np
import itertools
import multiprocessing
import time
from tqdm import tqdm
import json
import matplotlib.pyplot as plt
from functools import partial
import logging
from concurrent.futures import ProcessPoolExecutor
import optuna
from optuna.pruners import MedianPruner
from deap import base, creator, tools, algorithms
import random
import sys
import ctypes
import platform

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入回测策略
import backtest

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def prevent_sleep():
    """防止系统休眠"""
    if platform.system() == 'Windows':
        # Windows系统
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
    elif platform.system() == 'Darwin':
        # macOS系统
        os.system('caffeinate -i &')
    elif platform.system() == 'Linux':
        # Linux系统
        os.system('systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target')

def allow_sleep():
    """允许系统休眠"""
    if platform.system() == 'Windows':
        # Windows系统
        ES_CONTINUOUS = 0x80000000
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    elif platform.system() == 'Darwin':
        # macOS系统
        os.system('killall caffeinate')
    elif platform.system() == 'Linux':
        # Linux系统
        os.system('systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target')

class ParameterOptimizer:
    """参数优化器类，用于寻找最佳参数组合"""
    
    def __init__(self, stock_files, method='grid_search', n_jobs=-1, output_dir='optimization_results'):
        """
        初始化参数优化器
        
        参数:
            stock_files (list): 股票数据文件列表
            method (str): 优化方法，可选 'grid_search', 'bayesian', 'genetic'
            n_jobs (int): 并行作业数，-1表示使用所有可用CPU
            output_dir (str): 结果输出目录
        """
        # 使用所有股票进行测试
        self.stock_files = stock_files
        self.method = method
        self.n_jobs = multiprocessing.cpu_count()  # 使用所有CPU核心
        self.output_dir = output_dir
        self.best_params = None
        self.best_score = float('-inf')
        self.results_history = []
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 防止系统休眠
        prevent_sleep()
        
    def __del__(self):
        """析构函数，确保允许系统休眠"""
        allow_sleep()
        
    def define_param_space(self):
        """定义参数搜索空间"""
        param_space = {
            # V型转折参数
            'VSHAPE_PREV_PRICE_POSITION': [0.16, 0.17, 0.18],  # 以0.17为中心
            'VSHAPE_PCT_CHG_MIN': [0, 1, 2, 3, 4, 5],  # 以3.0为中心
            
            # V型转折条件参数
            'VSHAPE_CONDITION1': {
                'min_slope': [-0.011, -0.01, -0.009],  # 以-0.01为中心
                'max_slope': [-0.0008, -0.0007, -0.0006],  # 以-0.0007为中心
                'prev_rsd': [6.25, 6.5, 6.75]  # 以6.5为中心
            },
            'VSHAPE_CONDITION2': {
                'min_slope': [-0.065, -0.06, -0.055],  # 以-0.06为中心
                'max_slope': [-0.016, -0.015, -0.014],  # 以-0.015为中心
                'prev_rsd': [7.75, 8.0, 8.25]  # 以8.0为中心
            },
            'VSHAPE_CONDITION3': {
                'min_slope': [-0.125, -0.12, -0.115],  # 以-0.12为中心
                'max_slope': [-0.046, -0.045, -0.044],  # 以-0.045为中心
                'prev_rsd': [7.25, 7.5, 7.75]  # 以7.5为中心
            },
            'VSHAPE_CONDITION4': {
                'min_slope': [-0.155, -0.15, -0.145],  # 以-0.15为中心
                'max_slope': [-0.121, -0.12, -0.119],  # 以-0.12为中心
                'prev_rsd': [9.75, 10.0, 10.25]  # 以10.0为中心
            },
            'VSHAPE_CONDITION5': {
                'min_slope': [-0.175, -0.17, -0.165],  # 以-0.17为中心
                'max_slope': [-0.136, -0.135, -0.134],  # 以-0.135为中心
                'prev_rsd': [11.5, 11.75, 12.0]  # 以11.75为中心
            },
            'VSHAPE_CONDITION6': {
                'min_slope': [-0.295, -0.29, -0.285],  # 以-0.29为中心
                'max_slope': [-0.176, -0.175, -0.174],  # 以-0.175为中心
                'prev_rsd': [15.75, 16.0, 16.25]  # 以16.0为中心
            },
            'VSHAPE_CONDITION7': {
                'min_slope': [-0.29, -0.285, -0.28],  # 以-0.285为中心
                'max_slope': [float('inf')],
                'prev_rsd': [20.25, 20.5, 20.75]  # 以20.5为中心
            },
            
            # 买入条件配置
            'BUY_CONDITION1': {
                'MAIN_NET_RATE_MIN': [0.18, 0.2, 0.22],  # 以0.2为中心
                'PCT_CHG_MIN': [4.5, 5.0, 5.5]  # 以5.0为中心
            },
            'BUY_CONDITION4': {
                'CLOSE_SLOPE_MIN': [0.075, 0.08, 0.085],  # 以0.08为中心
                'PREV_RSD_MAX': [4.75, 5.0, 5.25],  # 以5.0为中心
                'RSD_CHG_MIN': [0.20, 0.21, 0.22]  # 以0.21为中心
            },
            
            # 卖出条件配置
            'SELL_CONDITION1': {
                'RSD_MIN': [2.0, 2.25, 2.5],  # 以2.25为中心
                'RSD_MAX': [6.25, 6.5, 6.75],  # 以6.5为中心
                'PRICE_TO_LOW_MIN': [1.35, 1.4, 1.45]  # 以1.4为中心
            },
            'SELL_CONDITION2': {
                'RSD_MIN': [7.25, 7.5, 7.75],  # 以7.5为中心
                'RSD_MAX': [10.25, 10.5, 10.75],  # 以10.5为中心
                'PRICE_TO_LOW_MIN': [1.4, 1.45, 1.5]  # 以1.45为中心
            },
            'SELL_CONDITION3': {
                'RSD_MIN': [12.25, 12.5, 12.75],  # 以12.5为中心
                'RSD_MAX': [15.25, 15.5, 15.75],  # 以15.5为中心
                'PRICE_TO_LOW_MIN': [1.75, 1.8, 1.85]  # 以1.8为中心
            },
            'SELL_CONDITION4': {
                'RSD_MIN': [14.25, 14.5, 14.75],  # 以14.5为中心
                'RSD_MAX': [18.75, 19.0, 19.25],  # 以19.0为中心
                'PRICE_TO_LOW_MIN': [2.0, 2.05, 2.1]  # 以2.05为中心
            },
            'SELL_CONDITION5': {
                'RSD_MIN': [19.75, 20.0, 20.25],  # 以20.0为中心
                'RSD_MAX': [24.25, 24.5, 24.75],  # 以24.5为中心
                'PRICE_TO_LOW_MIN': [2.15, 2.2, 2.25]  # 以2.2为中心
            },
            'SELL_CONDITION6': {
                'RSD_MIN': [24.75, 25.0, 25.25],  # 以25.0为中心
                'RSD_MAX': [30.25, 30.5, 30.75],  # 以30.5为中心
                'PRICE_TO_LOW_MIN': [2.45, 2.5, 2.55]  # 以2.5为中心
            },
            'SELL_CONDITION7': {
                'RSD_MIN': [30.75, 31.0, 31.25],  # 以31.0为中心
                'RSD_MAX': [float('inf')],
                'PRICE_TO_LOW_MIN': [3.05, 3.1, 3.15]  # 以3.1为中心
            },
            
            # 公共卖出条件
            'SELL_COMMON': {
                'PRICE_POSITION_CROSS': [-1],
                'PRICE_POSITION_MIN': [0.79, 0.8, 0.81]  # 以0.8为中心
            }
        }
        
        return param_space
    
    def apply_params_to_strategy(self, params):
        """将扁平化的参数转换为嵌套字典格式并应用到策略配置类"""
        # 将扁平化的参数转换为嵌套字典格式
        nested_params = {}
        
        # 处理V型转折参数
        nested_params['VSHAPE_PREV_PRICE_POSITION'] = params.get('VSHAPE_PREV_PRICE_POSITION', 0.17)
        nested_params['VSHAPE_PCT_CHG_MIN'] = params.get('VSHAPE_PCT_CHG_MIN', 3.0)
        
        # 处理V型转折条件
        vshape_conditions = []
        for i in range(1, 8):
            condition = {
                'min_slope': params.get(f'VSHAPE_CONDITION{i}_min_slope', -0.01),
                'max_slope': params.get(f'VSHAPE_CONDITION{i}_max_slope', -0.0006),
                'prev_rsd': params.get(f'VSHAPE_CONDITION{i}_prev_rsd', 6.5)
            }
            vshape_conditions.append(condition)
        nested_params['VSHAPE_CONDITIONS'] = vshape_conditions
        
        # 处理买入条件
        buy_conditions = {
            'CONDITION1': {
                'MAIN_NET_RATE_MIN': params.get('BUY_CONDITION1_MAIN_NET_RATE_MIN', 0.2),
                'PCT_CHG_MIN': params.get('BUY_CONDITION1_PCT_CHG_MIN', 5.0)
            },
            'CONDITION4': {
                'CLOSE_SLOPE_MIN': params.get('BUY_CONDITION4_CLOSE_SLOPE_MIN', 0.08),
                'PREV_RSD_MAX': params.get('BUY_CONDITION4_PREV_RSD_MAX', 5.0),
                'RSD_CHG_MIN': params.get('BUY_CONDITION4_RSD_CHG_MIN', 0.21)
            }
        }
        nested_params['BUY_CONDITIONS'] = buy_conditions
        
        # 处理卖出条件
        sell_conditions = []
        for i in range(1, 8):
            condition = {
                'RSD_MIN': params.get(f'SELL_CONDITION{i}_RSD_MIN', 2.5),
                'RSD_MAX': params.get(f'SELL_CONDITION{i}_RSD_MAX', 6.5),
                'PRICE_TO_LOW_MIN': params.get(f'SELL_CONDITION{i}_PRICE_TO_LOW_MIN', 1.4)
            }
            sell_conditions.append(condition)
        nested_params['SELL_CONDITIONS'] = sell_conditions
        
        # 处理公共卖出条件
        sell_common = {
            'PRICE_POSITION_CROSS': params.get('SELL_COMMON_PRICE_POSITION_CROSS', -1),
            'PRICE_POSITION_MIN': params.get('SELL_COMMON_PRICE_POSITION_MIN', 0.8)
        }
        nested_params['SELL_COMMON_CONDITIONS'] = sell_common
        
        # 更新策略配置
        config = backtest.StrategyConfig(nested_params)
        
        return config
    
    def run_backtest_with_params(self, params):
        """
        使用指定参数运行回测
        
        参数:
            params (dict): 参数字典
            
        返回:
            dict: 回测结果，包含总收益率、胜率等
        """
        try:
            # 应用参数
            self.apply_params_to_strategy(params)
            
            # 记录当前正在测试的参数
            logging.info(f"正在测试参数: {params}")
            
            # 获取测试股票数量
            total_stocks = len(self.stock_files)
            test_stocks = self.stock_files  # 使用全部测试股票
            logging.info(f"测试股票总数: {len(test_stocks)}")
            
            # 运行回测
            all_results = []
            for stock_file in test_stocks:
                try:
                    stock_code = os.path.basename(stock_file).split('_')[0]
                    logging.info(f"正在回测股票: {stock_code}")
                    
                    # 检查文件是否存在
                    if not os.path.exists(stock_file):
                        logging.error(f"股票文件不存在: {stock_file}")
                        continue
                        
                    # 检查文件是否为空
                    if os.path.getsize(stock_file) == 0:
                        logging.error(f"股票文件为空: {stock_file}")
                        continue
                        
                    results = backtest.backtest_strategy(stock_file)
                    
                    # 检查回测结果是否有效
                    if results['trades'] > 0:
                        all_results.append(results)
                        logging.info(f"回测完成: {stock_code} - 交易次数={results['trades']}, 收益率={results['profit_rate']:.2f}%")
                    else:
                        logging.warning(f"股票 {stock_code} 没有产生交易")
                        
                except Exception as e:
                    logging.error(f"回测股票 {stock_file} 时出错: {str(e)}")
                    continue
            
            # 计算汇总结果
            if not all_results:
                logging.warning("没有产生任何有效交易")
                return {'profit_rate': -999, 'win_rate': 0, 'trades': 0}
                
            total_trades = sum(r['trades'] for r in all_results)
            total_profit = sum(r['total_profit'] for r in all_results)
            
            if total_trades == 0:
                logging.warning("没有产生任何交易")
                return {'profit_rate': -999, 'win_rate': 0, 'trades': 0}
            
            # 计算平均收益率
            initial_amount = 100000  # 使用固定的初始资金金额
            total_initial_capital = initial_amount * len(all_results)
            total_return = (total_profit / total_initial_capital) * 100
            
            # 计算平均胜率
            win_trades = sum(r['trades'] * r['win_rate'] for r in all_results)
            win_rate = win_trades / total_trades if total_trades > 0 else 0
            
            logging.info(f"参数评估完成: 总交易={total_trades}, 总收益率={total_return:.2f}%, 胜率={win_rate:.2%}")
            
            return {
                'profit_rate': total_return,
                'win_rate': win_rate,
                'trades': total_trades,
                'params': params
            }
            
        except Exception as e:
            logging.error(f"回测出错: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return {'profit_rate': -999, 'win_rate': 0, 'trades': 0}
    
    def evaluate_params(self, params):
        """
        评估参数组合，返回评分
        
        参数:
            params (dict): 参数字典
            
        返回:
            float: 参数评分
        """
        result = self.run_backtest_with_params(params)
        
        # 计算综合评分：收益率 * 0.6 + 胜率 * 0.4，但要求至少有5笔交易
        profit_rate = result['profit_rate']
        win_rate = result['win_rate']
        trades = result['trades']
        
        if trades < 5:
            return -999  # 交易次数太少，评分降低
        
        # 综合评分
        score = profit_rate * 0.6 + win_rate * 100 * 0.4
        
        # 记录结果
        self.results_history.append({
            'params': params,
            'profit_rate': profit_rate,
            'win_rate': win_rate,
            'trades': trades,
            'score': score
        })
        
        # 更新最佳参数
        if score > self.best_score:
            self.best_score = score
            self.best_params = params.copy()
            logging.info(f"找到更好的参数组合: 评分={score:.2f}, 收益率={profit_rate:.2f}%, 胜率={win_rate:.2%}, 交易次数={trades}")
        
        return score
    
    def grid_search(self):
        """
        网格搜索找最佳参数
        
        返回:
            dict: 最佳参数组合
        """
        param_space = self.define_param_space()
        
        # 生成参数组合
        param_combinations = []
        
        # 处理V型转折参数
        vshape_position = param_space['VSHAPE_PREV_PRICE_POSITION']
        
        # 处理V型转折条件
        vshape_conditions = []
        for i in range(1, 8):
            condition = param_space[f'VSHAPE_CONDITION{i}']
            vshape_conditions.append(condition)
        
        # 处理买入条件
        buy_condition = param_space['BUY_CONDITION4']
        
        # 处理卖出条件
        sell_conditions = []
        for i in range(1, 8):
            condition = param_space[f'SELL_CONDITION{i}']
            sell_conditions.append(condition)
        
        # 处理公共卖出条件
        sell_common = param_space['SELL_COMMON']
        
        # 生成所有可能的组合
        for pos in vshape_position:
            for v1 in itertools.product(
                vshape_conditions[0]['min_slope'],
                vshape_conditions[0]['max_slope'],
                vshape_conditions[0]['prev_rsd'],
                vshape_conditions[0]['pct_chg_min']
            ):
                for v2 in itertools.product(
                    vshape_conditions[1]['min_slope'],
                    vshape_conditions[1]['max_slope'],
                    vshape_conditions[1]['prev_rsd'],
                    vshape_conditions[1]['pct_chg_min']
                ):
                    for v3 in itertools.product(
                        vshape_conditions[2]['min_slope'],
                        vshape_conditions[2]['max_slope'],
                        vshape_conditions[2]['prev_rsd'],
                        vshape_conditions[2]['pct_chg_min']
                    ):
                        for v4 in itertools.product(
                            vshape_conditions[3]['min_slope'],
                            vshape_conditions[3]['max_slope'],
                            vshape_conditions[3]['prev_rsd'],
                            vshape_conditions[3]['pct_chg_min']
                        ):
                            for v5 in itertools.product(
                                vshape_conditions[4]['min_slope'],
                                vshape_conditions[4]['max_slope'],
                                vshape_conditions[4]['prev_rsd'],
                                vshape_conditions[4]['pct_chg_min']
                            ):
                                for v6 in itertools.product(
                                    vshape_conditions[5]['min_slope'],
                                    vshape_conditions[5]['max_slope'],
                                    vshape_conditions[5]['prev_rsd'],
                                    vshape_conditions[5]['pct_chg_min']
                                ):
                                    for v7 in itertools.product(
                                        vshape_conditions[6]['min_slope'],
                                        vshape_conditions[6]['max_slope'],
                                        vshape_conditions[6]['prev_rsd'],
                                        vshape_conditions[6]['pct_chg_min']
                                    ):
                                        for b in itertools.product(
                                            buy_condition['CLOSE_SLOPE_MIN'],
                                            buy_condition['PREV_RSD_MAX'],
                                            buy_condition['RSD_CHG_MIN']
                                        ):
                                            for s1 in itertools.product(
                                                sell_conditions[0]['RSD_MIN'],
                                                sell_conditions[0]['RSD_MAX'],
                                                sell_conditions[0]['PRICE_TO_LOW_MIN']
                                            ):
                                                for s2 in itertools.product(
                                                    sell_conditions[1]['RSD_MIN'],
                                                    sell_conditions[1]['RSD_MAX'],
                                                    sell_conditions[1]['PRICE_TO_LOW_MIN']
                                                ):
                                                    for s3 in itertools.product(
                                                        sell_conditions[2]['RSD_MIN'],
                                                        sell_conditions[2]['RSD_MAX'],
                                                        sell_conditions[2]['PRICE_TO_LOW_MIN']
                                                    ):
                                                        for s4 in itertools.product(
                                                            sell_conditions[3]['RSD_MIN'],
                                                            sell_conditions[3]['RSD_MAX'],
                                                            sell_conditions[3]['PRICE_TO_LOW_MIN']
                                                        ):
                                                            for s5 in itertools.product(
                                                                sell_conditions[4]['RSD_MIN'],
                                                                sell_conditions[4]['RSD_MAX'],
                                                                sell_conditions[4]['PRICE_TO_LOW_MIN']
                                                            ):
                                                                for s6 in itertools.product(
                                                                    sell_conditions[5]['RSD_MIN'],
                                                                    sell_conditions[5]['RSD_MAX'],
                                                                    sell_conditions[5]['PRICE_TO_LOW_MIN']
                                                                ):
                                                                    for s7 in itertools.product(
                                                                        sell_conditions[6]['RSD_MIN'],
                                                                        sell_conditions[6]['RSD_MAX'],
                                                                        sell_conditions[6]['PRICE_TO_LOW_MIN']
                                                                    ):
                                                                        for sc in sell_common['PRICE_POSITION_MIN']:
                                                                            # 构建参数字典
                                                                            params = {
                                                                                'VSHAPE_PREV_PRICE_POSITION': pos,
                                                                                'VSHAPE_CONDITION1_min_slope': v1[0],
                                                                                'VSHAPE_CONDITION1_max_slope': v1[1],
                                                                                'VSHAPE_CONDITION1_prev_rsd': v1[2],
                                                                                'VSHAPE_CONDITION1_pct_chg_min': v1[3],
                                                                                'VSHAPE_CONDITION2_min_slope': v2[0],
                                                                                'VSHAPE_CONDITION2_max_slope': v2[1],
                                                                                'VSHAPE_CONDITION2_prev_rsd': v2[2],
                                                                                'VSHAPE_CONDITION2_pct_chg_min': v2[3],
                                                                                'VSHAPE_CONDITION3_min_slope': v3[0],
                                                                                'VSHAPE_CONDITION3_max_slope': v3[1],
                                                                                'VSHAPE_CONDITION3_prev_rsd': v3[2],
                                                                                'VSHAPE_CONDITION3_pct_chg_min': v3[3],
                                                                                'VSHAPE_CONDITION4_min_slope': v4[0],
                                                                                'VSHAPE_CONDITION4_max_slope': v4[1],
                                                                                'VSHAPE_CONDITION4_prev_rsd': v4[2],
                                                                                'VSHAPE_CONDITION4_pct_chg_min': v4[3],
                                                                                'VSHAPE_CONDITION5_min_slope': v5[0],
                                                                                'VSHAPE_CONDITION5_max_slope': v5[1],
                                                                                'VSHAPE_CONDITION5_prev_rsd': v5[2],
                                                                                'VSHAPE_CONDITION5_pct_chg_min': v5[3],
                                                                                'VSHAPE_CONDITION6_min_slope': v6[0],
                                                                                'VSHAPE_CONDITION6_max_slope': v6[1],
                                                                                'VSHAPE_CONDITION6_prev_rsd': v6[2],
                                                                                'VSHAPE_CONDITION6_pct_chg_min': v6[3],
                                                                                'VSHAPE_CONDITION7_min_slope': v7[0],
                                                                                'VSHAPE_CONDITION7_max_slope': v7[1],
                                                                                'VSHAPE_CONDITION7_prev_rsd': v7[2],
                                                                                'VSHAPE_CONDITION7_pct_chg_min': v7[3],
                                                                                'BUY_CONDITION4_CLOSE_SLOPE_MIN': b[0],
                                                                                'BUY_CONDITION4_PREV_RSD_MAX': b[1],
                                                                                'BUY_CONDITION4_RSD_CHG_MIN': b[2],
                                                                                'SELL_CONDITION1_RSD_MIN': s1[0],
                                                                                'SELL_CONDITION1_RSD_MAX': s1[1],
                                                                                'SELL_CONDITION1_PRICE_TO_LOW_MIN': s1[2],
                                                                                'SELL_CONDITION2_RSD_MIN': s2[0],
                                                                                'SELL_CONDITION2_RSD_MAX': s2[1],
                                                                                'SELL_CONDITION2_PRICE_TO_LOW_MIN': s2[2],
                                                                                'SELL_CONDITION3_RSD_MIN': s3[0],
                                                                                'SELL_CONDITION3_RSD_MAX': s3[1],
                                                                                'SELL_CONDITION3_PRICE_TO_LOW_MIN': s3[2],
                                                                                'SELL_CONDITION4_RSD_MIN': s4[0],
                                                                                'SELL_CONDITION4_RSD_MAX': s4[1],
                                                                                'SELL_CONDITION4_PRICE_TO_LOW_MIN': s4[2],
                                                                                'SELL_CONDITION5_RSD_MIN': s5[0],
                                                                                'SELL_CONDITION5_RSD_MAX': s5[1],
                                                                                'SELL_CONDITION5_PRICE_TO_LOW_MIN': s5[2],
                                                                                'SELL_CONDITION6_RSD_MIN': s6[0],
                                                                                'SELL_CONDITION6_RSD_MAX': s6[1],
                                                                                'SELL_CONDITION6_PRICE_TO_LOW_MIN': s6[2],
                                                                                'SELL_CONDITION7_RSD_MIN': s7[0],
                                                                                'SELL_CONDITION7_RSD_MAX': s7[1],
                                                                                'SELL_CONDITION7_PRICE_TO_LOW_MIN': s7[2],
                                                                                'SELL_COMMON_PRICE_POSITION_CROSS': -1,
                                                                                'SELL_COMMON_PRICE_POSITION_MIN': sc
                                                                            }
                                                                            param_combinations.append(params)
        
        # 如果组合数太多，进行随机抽样
        if len(param_combinations) > 10000:
            logging.info(f"参数组合过多，进行随机抽样...")
            param_combinations = random.sample(param_combinations, 10000)
        
        logging.info(f"开始评估 {len(param_combinations)} 个参数组合")
        
        # 并行评估参数组合
        with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
            results = list(tqdm(
                executor.map(self.evaluate_params, param_combinations),
                total=len(param_combinations),
                desc="网格搜索进度"
            ))
        
        # 保存所有结果
        self.save_results()
        
        return self.best_params
    
    def bayesian_optimization(self, n_trials=40):
        """贝叶斯优化找最佳参数"""
        param_space = self.define_param_space()
        
        def objective(trial):
            # 构建参数
            params = {}
            for key, values in param_space.items():
                if isinstance(values, list):
                    params[key] = trial.suggest_categorical(key, values)
                elif isinstance(values, dict):
                    for sub_key, sub_values in values.items():
                        param_name = f"{key}_{sub_key}"
                        if isinstance(sub_values, list):
                            params[param_name] = trial.suggest_categorical(param_name, sub_values)
                        else:
                            params[param_name] = sub_values
            
            # 确保 VSHAPE_PCT_CHG_MIN 参数存在
            if 'VSHAPE_PCT_CHG_MIN' not in params:
                params['VSHAPE_PCT_CHG_MIN'] = trial.suggest_categorical('VSHAPE_PCT_CHG_MIN', param_space['VSHAPE_PCT_CHG_MIN'])
            
            # 评估参数
            logging.info(f"开始评估试验 #{trial.number}")
            score = self.evaluate_params(params)
            logging.info(f"试验 #{trial.number} 评分: {score}")
            
            if score < -500:
                trial.report(-1, step=1)
                raise optuna.TrialPruned()
            
            return -score
        
        # 创建学习器，使用TPESampler并设置n_startup_trials
        sampler = optuna.samplers.TPESampler(
            n_startup_trials=10,  # 增加随机搜索次数
            n_ei_candidates=15,   # 增加候选点数量
            seed=42,              # 固定随机种子以保证结果可复现
        )
        
        study = optuna.create_study(
            direction='minimize',
            sampler=sampler,
            pruner=MedianPruner(),  # 在创建study时使用MedianPruner
            study_name='parameter_optimization'
        )
        
        # 创建自定义回调函数，在连续n_steps次没有改善时停止
        class CustomStopCallback:
            def __init__(self, n_steps=15, interval_steps=3):  # 增加停止条件
                self.n_steps = n_steps
                self.interval_steps = interval_steps
                self.best_value = float('inf')
                self.n_steps_without_improvement = 0
                
            def __call__(self, study, trial):
                if trial.number % self.interval_steps == 0:
                    current_best = study.best_value
                    if current_best < self.best_value:
                        self.best_value = current_best
                        self.n_steps_without_improvement = 0
                    else:
                        self.n_steps_without_improvement += self.interval_steps
                        
                    if self.n_steps_without_improvement >= self.n_steps:
                        study.stop()
        
        try:
            # 设置优化目标
            study.optimize(
                objective,
                n_trials=n_trials,
                callbacks=[
                    CustomStopCallback(n_steps=15, interval_steps=3)  # 调整早停条件
                ],
                gc_after_trial=True,  # 每次试验后进行垃圾回收
                show_progress_bar=True  # 显示进度条
            )
            
            # 获取最佳参数
            if study.best_trial:
                self.best_params = study.best_params
                self.best_score = -study.best_value
            else:
                logging.warning("优化未完成，使用初始参数")
                self.best_params = self.define_default_params()
            
            # 保存所有结果
            self.save_results()
            
            # 输出优化过程统计
            logging.info(f"\n优化过程统计:")
            logging.info(f"总试验次数: {len(study.trials)}")
            logging.info(f"被剪枝的试验数: {len(study.get_trials(states=[optuna.trial.TrialState.PRUNED]))}")
            logging.info(f"完成试验数: {len(study.get_trials(states=[optuna.trial.TrialState.COMPLETE]))}")
            
            return self.best_params
        
        except Exception as e:
            logging.error(f"优化过程中出错: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            # 返回默认参数
            return self.define_default_params()
    
    def define_default_params(self):
        """定义默认参数，在优化失败时使用"""
        return {
            'VSHAPE_PREV_PRICE_POSITION': 0.1,
            'VSHAPE_CONDITION1': {'min_slope': -0.01, 'max_slope': -0.001, 'prev_rsd': 6.0, 'pct_chg_min': 3.0},
            'VSHAPE_CONDITION2': {'min_slope': -0.05, 'max_slope': -0.01, 'prev_rsd': 8.0, 'pct_chg_min': 3.0},
            'VSHAPE_CONDITION3': {'min_slope': -0.12, 'max_slope': -0.05, 'prev_rsd': 9.0, 'pct_chg_min': 3.0},
            'VSHAPE_CONDITION4': {'min_slope': -0.15, 'max_slope': -0.1, 'prev_rsd': 11.0, 'pct_chg_min': 3.0},
            'VSHAPE_CONDITION5': {'min_slope': -0.21, 'max_slope': -0.15, 'prev_rsd': 11.0, 'pct_chg_min': 3.0},
            'VSHAPE_CONDITION6': {'min_slope': -0.27, 'max_slope': -0.22, 'prev_rsd': 14.0, 'pct_chg_min': 3.0},
            'VSHAPE_CONDITION7': {'min_slope': -0.28, 'max_slope': float('inf'), 'prev_rsd': 20.0, 'pct_chg_min': 3.0},
            'BUY_CONDITION4': {'CLOSE_SLOPE_MIN': 0.05, 'PREV_RSD_MAX': 5.5, 'RSD_CHG_MIN': 0.2},
            'SELL_CONDITION1': {'RSD_MIN': 2.5, 'RSD_MAX': 6.5, 'PRICE_TO_LOW_MIN': 1.4},
            'SELL_CONDITION2': {'RSD_MIN': 6.5, 'RSD_MAX': 11.5, 'PRICE_TO_LOW_MIN': 1.6},
            'SELL_CONDITION3': {'RSD_MIN': 11.5, 'RSD_MAX': 15.5, 'PRICE_TO_LOW_MIN': 1.8},
            'SELL_CONDITION4': {'RSD_MIN': 15.5, 'RSD_MAX': 20.0, 'PRICE_TO_LOW_MIN': 2.0},
            'SELL_CONDITION5': {'RSD_MIN': 20.0, 'RSD_MAX': 25.0, 'PRICE_TO_LOW_MIN': 2.2},
            'SELL_CONDITION6': {'RSD_MIN': 25.0, 'RSD_MAX': 30.0, 'PRICE_TO_LOW_MIN': 2.5},
            'SELL_CONDITION7': {'RSD_MIN': 30.0, 'RSD_MAX': float('inf'), 'PRICE_TO_LOW_MIN': 3.0},
            'SELL_COMMON': {'PRICE_POSITION_CROSS': -1, 'PRICE_POSITION_MIN': 0.85}
        }
    
    def genetic_algorithm(self, n_generations=20, population_size=50):
        """
        遗传算法找最佳参数
        
        参数:
            n_generations (int): 进化代数
            population_size (int): 种群大小
            
        返回:
            dict: 最佳参数组合
        """
        param_space = self.define_param_space()
        param_keys = list(param_space.keys())
        
        # 创建适应度类和个体类
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
        
        # 创建工具箱
        toolbox = base.Toolbox()
        
        # 定义个体和种群
        def create_individual():
            return [random.randint(0, len(param_space[key])-1) for key in param_keys]
        
        toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        
        # 定义评估函数
        def evaluate_individual(individual):
            # 将索引转换为实际参数值
            params = {}
            for i, key in enumerate(param_keys):
                params[key] = param_space[key][individual[i]]
            
            score = self.evaluate_params(params)
            return (score,)
        
        toolbox.register("evaluate", evaluate_individual)
        
        # 定义选择、交叉和变异操作
        toolbox.register("select", tools.selTournament, tournsize=3)
        toolbox.register("mate", tools.cxTwoPoint)
        toolbox.register("mutate", tools.mutUniformInt, 
                         low=0, up=[len(param_space[key])-1 for key in param_keys], 
                         indpb=0.2)
        
        # 创建种群
        pop = toolbox.population(n=population_size)
        hof = tools.HallOfFame(5)  # 保存最优的5个个体
        
        # 记录统计信息
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("min", np.min)
        stats.register("max", np.max)
        
        # 运行算法
        pop, logbook = algorithms.eaSimple(
            pop, toolbox, cxpb=0.7, mutpb=0.2, 
            ngen=n_generations, stats=stats, halloffame=hof, verbose=True
        )
        
        # 获取最佳个体
        best_individual = hof[0]
        
        # 将索引转换为参数值
        best_params = {}
        for i, key in enumerate(param_keys):
            best_params[key] = param_space[key][best_individual[i]]
        
        self.best_params = best_params
        
        # 保存所有结果
        self.save_results()
        
        return best_params
    
    def optimize(self):
        """
        根据选择的方法进行优化
        
        返回:
            dict: 最佳参数组合
        """
        start_time = time.time()
        
        if self.method == 'grid_search':
            self.best_params = self.grid_search()
        elif self.method == 'bayesian':
            self.best_params = self.bayesian_optimization()
        elif self.method == 'genetic':
            self.best_params = self.genetic_algorithm()
        else:
            raise ValueError(f"不支持的优化方法: {self.method}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        logging.info(f"优化完成，耗时: {duration:.2f}秒")
        logging.info(f"最佳参数: {self.best_params}")
        logging.info(f"最佳评分: {self.best_score:.2f}")
        
        # 使用最佳参数再次运行回测
        self.apply_params_to_strategy(self.best_params)
        results = self.run_backtest_with_params(self.best_params)
        
        print("\n=============================")
        logging.info(f"最佳参数回测结果:")
        logging.info(f"总收益率: {results['profit_rate']:.2f}%")
        logging.info(f"胜率: {results['win_rate']:.2%}")
        logging.info(f"交易次数: {results['trades']}")
        print("=============================\n")
        

        return self.best_params
    
    def save_results(self):
        """保存优化结果"""
        # 保存参数历史
        history_df = pd.DataFrame(self.results_history)
        history_df.to_csv(os.path.join(self.output_dir, f"{self.method}_history.csv"), index=False)
        
        # 保存最佳参数
        with open(os.path.join(self.output_dir, f"{self.method}_best_params.json"), 'w') as f:
            json.dump(self.best_params, f, indent=4)
        
        # 绘制参数与收益率关系图
        self.plot_results()
    
    def plot_results(self):
        """绘制优化结果可视化图表"""
        # 配置中文字体支持
        try:
            # 尝试设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
            plt.rcParams['axes.unicode_minus'] = False    # 用来正常显示负号
            logging.info("成功设置中文字体")
        except Exception as e:
            logging.warning(f"设置中文字体时出错: {str(e)}")
        
        # 转换为DataFrame便于处理
        history_df = pd.DataFrame(self.results_history)
        
        if len(history_df) == 0:
            return
        
        # 按收益率排序
        history_df.sort_values('profit_rate', ascending=False, inplace=True)
        
        # 绘制收益率分布
        plt.figure(figsize=(10, 6))
        plt.hist(history_df['profit_rate'], bins=30, alpha=0.7)
        plt.axvline(x=history_df['profit_rate'].iloc[0], color='r', linestyle='--', 
                   label=f'最佳收益率: {history_df["profit_rate"].iloc[0]:.2f}%')
        plt.xlabel('收益率 (%)')
        plt.ylabel('参数组合数')
        plt.title('参数优化 - 收益率分布')
        plt.legend()
        plt.savefig(os.path.join(self.output_dir, f"{self.method}_profit_distribution.png"), dpi=300)
        plt.close()
        
        # 绘制收益率与胜率的散点图
        plt.figure(figsize=(10, 6))
        plt.scatter(history_df['win_rate'], history_df['profit_rate'], 
                   c=history_df['trades'], cmap='viridis', alpha=0.7)
        plt.colorbar(label='交易次数')
        plt.scatter(history_df['win_rate'].iloc[0], history_df['profit_rate'].iloc[0], 
                   color='r', s=100, marker='*', label='最佳组合')
        plt.xlabel('胜率')
        plt.ylabel('收益率 (%)')
        plt.title('参数优化 - 收益率 vs 胜率')
        plt.legend()
        plt.savefig(os.path.join(self.output_dir, f"{self.method}_profit_vs_winrate.png"), dpi=300)
        plt.close()

def main():
    """主函数"""
    # 获取股票文件列表
    test_folder = 'test'
    stock_files = [os.path.join(test_folder, f) for f in os.listdir(test_folder) 
                  if f.endswith('_integrated.csv')]
    
    if not stock_files:
        raise FileNotFoundError(f"test文件夹中没有找到任何integrated.csv文件")
    
    # 创建参数优化器
    optimizer = ParameterOptimizer(
        stock_files=stock_files,
        method='bayesian',  # 使用贝叶斯优化方法
        n_jobs=multiprocessing.cpu_count() // 2,  # 使用一半的CPU核心
        output_dir='optimization_results'
    )
    
    # 运行优化
    best_params = optimizer.optimize()
    
    # 应用最佳参数到策略配置
    print("\n最佳参数组合:")
    for key, value in best_params.items():
        print(f"{key}: {value}")
    
    # 修改backtest.py中的策略参数
    print("\n请将以上参数更新到backtest.py中的StrategyConfig类中")

if __name__ == "__main__":
    main()  # 只调用一次main() 