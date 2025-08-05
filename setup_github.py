#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub设置脚本 - 配置并推送代码到GitHub
"""

import subprocess
import sys
import os
import logging

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def run_command(command, description):
    """运行命令并处理结果"""
    print(f"正在{description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description}成功")
            if result.stdout:
                print(f"输出: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description}失败")
            if result.stderr:
                print(f"错误: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description}出错: {e}")
        return False

def main():
    """主函数"""
    setup_logging()
    print("=== GitHub配置和推送脚本 ===")
    
    # 步骤1: 添加所有文件
    if not run_command("git add .", "添加文件到暂存区"):
        return False
    
    # 步骤2: 提交更改
    commit_message = "初始提交：MySQL量化交易策略研究项目"
    if not run_command(f'git commit -m "{commit_message}"', "提交更改"):
        return False
    
    # 步骤3: 推送到GitHub
    print("正在推送到GitHub...")
    print("注意：首次推送可能需要输入GitHub用户名和密码或个人访问令牌")
    
    if not run_command("git push -u origin main", "推送到GitHub"):
        print("\n推送失败的可能原因：")
        print("1. 需要配置GitHub认证")
        print("2. 网络连接问题")
        print("3. 仓库权限问题")
        print("\n建议：")
        print("1. 在GitHub设置中创建个人访问令牌")
        print("2. 使用令牌作为密码进行认证")
        return False
    
    print("\n🎉 GitHub配置和推送完成！")
    print("你的代码已经成功推送到: https://github.com/hgy2008v/mysql-strategy-research")
    return True

if __name__ == "__main__":
    main() 