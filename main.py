import logging
import time
import sys
import argparse
from logging_config import setup_logging, set_log_level
from download_stock_daily_incremental import process_incremental_download
from process_stock_data_incremental import process_incremental_data
from download_other_data import main as download_other_data_main

def main():
    """主函数 - 执行完整的数据处理流程"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='股票数据处理系统')
    parser.add_argument(
        '--log-level', 
        choices=['quiet', 'normal', 'verbose'], 
        default='normal',
        help='日志级别: quiet(只显示警告和错误), normal(显示信息), verbose(显示所有)'
    )
    parser.add_argument(
        '--log-file',
        help='日志文件路径（可选）'
    )
    parser.add_argument(
        '--download-only',
        action='store_true',
        help='只执行数据下载，不执行数据处理'
    )
    parser.add_argument(
        '--process-only',
        action='store_true',
        help='只执行数据处理，不执行数据下载'
    )
    parser.add_argument(
        '--skip-other-data',
        action='store_true',
        help='跳过其他市场数据下载'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别
    set_log_level(args.log_level)
    
    # 如果指定了日志文件，添加到文件处理器
    if args.log_file:
        setup_logging(log_file=args.log_file)
    
    start_time = time.time()
    
    try:
        print("=== 股票数据处理系统 ===")
        print(f"日志级别: {args.log_level}")
        if args.log_file:
            print(f"日志文件: {args.log_file}")
        if args.download_only:
            print("模式: 仅下载数据")
        elif args.process_only:
            print("模式: 仅处理数据")
        else:
            print("模式: 完整流程")
        if args.skip_other_data:
            print("跳过其他市场数据下载")
        print()
        
        logging.info("=== 开始股票数据处理流程 ===")
        
        # 根据参数决定执行哪些步骤
        if not args.process_only:
            # 步骤1: 增量下载股票日线数据
            logging.info("步骤1: 增量下载股票日线数据")
            process_incremental_download()
            
            # 步骤2: 下载其他市场数据
            if not args.skip_other_data:
                logging.info("步骤2: 下载其他市场数据")
                download_other_data_main()
        
        if not args.download_only:
            # 步骤3: 增量处理股票数据（计算技术指标）
            logging.info("步骤3: 增量处理股票数据（计算技术指标）")
            process_incremental_data()
        
        logging.info("=== 股票数据处理流程完成 ===")
        
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