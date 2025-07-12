#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动推送定时任务设置脚本
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("auto_push_scheduler.log"),
            logging.StreamHandler()
        ]
    )

def create_auto_push_task():
    """创建自动推送定时任务"""
    try:
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        auto_push_script = os.path.join(current_dir, "auto_push.py")
        
        # 检查auto_push.py是否存在
        if not os.path.exists(auto_push_script):
            logging.error(f"auto_push.py文件不存在: {auto_push_script}")
            return False
        
        # 任务配置
        task_name = "AutoPushToGitHub"
        run_time = "20:00"  # 每天晚上8:00运行
        
        # 构建命令
        cmd = [
            "schtasks", "/create", "/tn", task_name,
            "/tr", f"python \"{auto_push_script}\"",
            "/sc", "daily",
            "/st", run_time,
            "/f"
        ]
        
        logging.info("正在创建自动推送定时任务...")
        logging.info(f"任务名称: {task_name}")
        logging.info(f"运行时间: 每天 {run_time}")
        logging.info(f"脚本路径: {auto_push_script}")
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("自动推送定时任务创建成功！")
            print("\n=== 自动推送定时任务创建成功 ===")
            print(f"任务名称: {task_name}")
            print(f"运行时间: 每天 {run_time}")
            print(f"脚本路径: {auto_push_script}")
            print("\n管理命令:")
            print(f"- 查看任务: schtasks /query /tn {task_name}")
            print(f"- 删除任务: schtasks /delete /tn {task_name} /f")
            print(f"- 立即运行: schtasks /run /tn {task_name}")
            return True
        else:
            logging.error(f"创建任务失败: {result.stderr}")
            print(f"创建任务失败: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"创建定时任务时出错: {e}")
        print(f"创建定时任务时出错: {e}")
        return False

def delete_auto_push_task():
    """删除自动推送定时任务"""
    try:
        task_name = "AutoPushToGitHub"
        cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
        
        logging.info("正在删除自动推送定时任务...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("自动推送定时任务删除成功！")
            print("自动推送定时任务删除成功！")
            return True
        else:
            logging.error(f"删除任务失败: {result.stderr}")
            print(f"删除任务失败: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"删除定时任务时出错: {e}")
        print(f"删除定时任务时出错: {e}")
        return False

def check_auto_push_task():
    """检查自动推送定时任务状态"""
    try:
        task_name = "AutoPushToGitHub"
        cmd = ["schtasks", "/query", "/tn", task_name]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("=== 自动推送定时任务状态 ===")
            print(result.stdout)
            return True
        else:
            print("自动推送定时任务不存在或查询失败")
            return False
            
    except Exception as e:
        logging.error(f"检查定时任务时出错: {e}")
        print(f"检查定时任务时出错: {e}")
        return False

def run_auto_push_now():
    """立即运行自动推送任务"""
    try:
        task_name = "AutoPushToGitHub"
        cmd = ["schtasks", "/run", "/tn", task_name]
        
        logging.info("正在立即运行自动推送任务...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("自动推送任务启动成功！")
            print("自动推送任务启动成功！")
            return True
        else:
            logging.error(f"启动任务失败: {result.stderr}")
            print(f"启动任务失败: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"启动任务时出错: {e}")
        print(f"启动任务时出错: {e}")
        return False

def main():
    """主函数"""
    setup_logging()
    
    print("=== GitHub自动推送定时任务管理工具 ===")
    print("1. 创建自动推送定时任务（每天晚上8:00运行）")
    print("2. 删除自动推送定时任务")
    print("3. 检查自动推送定时任务状态")
    print("4. 立即运行自动推送任务")
    print("5. 退出")
    
    while True:
        try:
            choice = input("\n请选择操作 (1-5): ").strip()
            
            if choice == "1":
                create_auto_push_task()
            elif choice == "2":
                delete_auto_push_task()
            elif choice == "3":
                check_auto_push_task()
            elif choice == "4":
                run_auto_push_now()
            elif choice == "5":
                print("退出程序")
                break
            else:
                print("无效选择，请输入1-5")
                
        except KeyboardInterrupt:
            print("\n程序被用户中断")
            break
        except Exception as e:
            logging.error(f"程序执行出错: {e}")
            print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main() 