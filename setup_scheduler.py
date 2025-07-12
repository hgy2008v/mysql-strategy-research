import os
import sys
import subprocess
import logging
from datetime import datetime, time

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("scheduler_setup.log"),
            logging.StreamHandler()
        ]
    )

def create_windows_task():
    """创建Windows定时任务"""
    try:
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(current_dir, "main.py")
        
        # 检查main.py是否存在
        if not os.path.exists(main_script):
            logging.error(f"main.py文件不存在: {main_script}")
            return False
        
        # 任务配置
        task_name = "StockDataDownload"
        run_time = "19:00"  # 每天晚上7:00运行
        
        # 构建命令 - 修复语法错误
        cmd = [
            "schtasks", "/create", "/tn", task_name,
            "/tr", f"python \"{main_script}\"",
            "/sc", "daily",
            "/st", run_time,
            "/f"
        ]
        
        logging.info("正在创建Windows定时任务...")
        logging.info(f"任务名称: {task_name}")
        logging.info(f"运行时间: 每天 {run_time}")
        logging.info(f"脚本路径: {main_script}")
        
        # 执行命令
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("定时任务创建成功！")
            print("\n=== 定时任务创建成功 ===")
            print(f"任务名称: {task_name}")
            print(f"运行时间: 每天 {run_time}")
            print(f"脚本路径: {main_script}")
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

def delete_windows_task():
    """删除Windows定时任务"""
    try:
        task_name = "StockDataDownload"
        cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
        
        logging.info("正在删除Windows定时任务...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("定时任务删除成功！")
            print("定时任务删除成功！")
            return True
        else:
            logging.error(f"删除任务失败: {result.stderr}")
            print(f"删除任务失败: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"删除定时任务时出错: {e}")
        print(f"删除定时任务时出错: {e}")
        return False

def check_windows_task():
    """检查Windows定时任务状态"""
    try:
        task_name = "StockDataDownload"
        cmd = ["schtasks", "/query", "/tn", task_name]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("=== 定时任务状态 ===")
            print(result.stdout)
            return True
        else:
            print("定时任务不存在或查询失败")
            return False
            
    except Exception as e:
        logging.error(f"检查定时任务时出错: {e}")
        print(f"检查定时任务时出错: {e}")
        return False

def run_task_now():
    """立即运行定时任务"""
    try:
        task_name = "StockDataDownload"
        cmd = ["schtasks", "/run", "/tn", task_name]
        
        logging.info("正在立即运行定时任务...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("任务启动成功！")
            print("任务启动成功！")
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
    
    print("=== 股票数据下载定时任务管理工具 ===")
    print("1. 创建定时任务（每天晚上7:00运行）")
    print("2. 删除定时任务")
    print("3. 检查定时任务状态")
    print("4. 立即运行任务")
    print("5. 退出")
    
    while True:
        try:
            choice = input("\n请选择操作 (1-5): ").strip()
            
            if choice == "1":
                create_windows_task()
            elif choice == "2":
                delete_windows_task()
            elif choice == "3":
                check_windows_task()
            elif choice == "4":
                run_task_now()
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