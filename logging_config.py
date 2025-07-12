import logging
import os
from datetime import datetime

def setup_logging(level=logging.INFO, log_file=None):
    """
    设置简洁的日志配置
    
    参数:
        level: 日志级别，默认INFO
        log_file: 日志文件路径，默认None（不写入文件）
    """
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 如果指定了日志文件，添加文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('pymysql').setLevel(logging.WARNING)

def get_logger(name):
    """获取指定名称的日志记录器"""
    return logging.getLogger(name)

# 预定义的日志级别
QUIET = logging.WARNING      # 只显示警告和错误
NORMAL = logging.INFO        # 显示信息、警告和错误
VERBOSE = logging.DEBUG      # 显示所有日志

def set_log_level(level_name):
    """设置日志级别"""
    level_map = {
        'quiet': QUIET,
        'normal': NORMAL,
        'verbose': VERBOSE
    }
    
    level = level_map.get(level_name.lower(), NORMAL)
    setup_logging(level)
    return level 