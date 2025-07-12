#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动推送脚本 - 定期将代码更改推送到GitHub
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
import time

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("auto_push.log"),
            logging.StreamHandler()
        ]
    )

def check_git_status():
    """检查Git状态"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        logging.error(f"检查Git状态失败: {e}")
        return None

def add_changes():
    """添加所有更改"""
    try:
        result = subprocess.run(['git', 'add', '.'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("文件已添加到暂存区")
            return True
        else:
            logging.error(f"添加文件失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"添加文件时出错: {e}")
        return False

def commit_changes(message=None):
    """提交更改"""
    try:
        if not message:
            message = f"自动更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        result = subprocess.run(['git', 'commit', '-m', message], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"提交成功: {message}")
            return True
        else:
            logging.error(f"提交失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"提交时出错: {e}")
        return False

def push_to_github():
    """推送到GitHub"""
    try:
        # 获取当前分支名
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("获取当前分支失败")
            return False
        
        current_branch = result.stdout.strip()
        
        # 推送到远程仓库
        result = subprocess.run(['git', 'push', 'origin', current_branch], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"推送成功到分支: {current_branch}")
            return True
        else:
            logging.error(f"推送失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"推送时出错: {e}")
        return False

def check_remote_repo():
    """检查远程仓库配置"""
    try:
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            logging.info("远程仓库已配置")
            return True
        else:
            logging.warning("未配置远程仓库")
            return False
    except Exception as e:
        logging.error(f"检查远程仓库时出错: {e}")
        return False

def auto_push():
    """自动推送主函数"""
    setup_logging()
    
    logging.info("开始自动推送流程...")
    
    # 检查远程仓库
    if not check_remote_repo():
        logging.error("请先配置远程仓库")
        print("请先配置远程仓库，使用命令：")
        print("git remote add origin <您的GitHub仓库URL>")
        return False
    
    # 检查是否有更改
    changes = check_git_status()
    if not changes:
        logging.info("没有需要提交的更改")
        return True
    
    logging.info(f"发现更改:\n{changes}")
    
    # 添加更改
    if not add_changes():
        return False
    
    # 提交更改
    if not commit_changes():
        return False
    
    # 推送到GitHub
    if not push_to_github():
        return False
    
    logging.info("自动推送完成！")
    return True

def setup_remote_repo(repo_url):
    """设置远程仓库"""
    try:
        result = subprocess.run(['git', 'remote', 'add', 'origin', repo_url], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"远程仓库配置成功: {repo_url}")
            return True
        else:
            logging.error(f"配置远程仓库失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"配置远程仓库时出错: {e}")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            if len(sys.argv) > 2:
                repo_url = sys.argv[2]
                setup_logging()
                if setup_remote_repo(repo_url):
                    print("远程仓库配置成功！")
                    print("现在可以运行: python auto_push.py")
                else:
                    print("远程仓库配置失败！")
            else:
                print("请提供GitHub仓库URL")
                print("用法: python auto_push.py setup <GitHub仓库URL>")
        else:
            print("未知参数")
            print("用法:")
            print("  python auto_push.py                    # 执行自动推送")
            print("  python auto_push.py setup <仓库URL>    # 配置远程仓库")
    else:
        auto_push()

if __name__ == "__main__":
    main() 