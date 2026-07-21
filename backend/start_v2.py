#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V2启动脚本 - 设置环境变量后启动服务和定时任务调度器
"""
import os
import sys
import subprocess
import socket
import threading

# 设置环境变量 - 从环境变量读取
# 生产环境必须通过环境变量设置 COOKIE_SECRET
# 开发环境使用临时密钥（仅用于本地开发）
os.environ.setdefault('ALLOWED_ORIGINS', 'http://localhost:5001')
os.environ.setdefault('DEBUG', 'True')
if not os.environ.get('COOKIE_SECRET'):
    print("警告: COOKIE_SECRET未设置，使用临时开发密钥！")
    print("生产环境请设置环境变量: export COOKIE_SECRET=your-secure-secret")
    os.environ['COOKIE_SECRET'] = 'dev-temp-secret-do-not-use-in-production'


def kill_port_process(port):
    """检查并杀掉占用指定端口的进程"""
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True, capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if 'LISTENING' in line and f':{port}' in line:
                parts = line.split()
                if parts[-1] != '0':
                    pid = parts[-1]
                    print(f"发现端口 {port} 被占用 (PID: {pid})，正在清理...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                    return True
    except Exception as e:
        print(f"检查端口时出错: {e}")
    return False


def wait_for_port(port, timeout=5):
    """等待端口释放"""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(('localhost', port))
            return False
        except:
            return True
    return False


def start_scheduler_in_background():
    """在后台线程中启动调度器"""
    try:
        from scheduler import start_scheduler
        scheduler = start_scheduler()
        print("[调度器] 定时任务调度器已在后台启动")
        return scheduler
    except Exception as e:
        print(f"[调度器] 启动调度器失败: {e}")
        import traceback
        traceback.print_exc()
        return None


os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config import API_PORT
PORT = API_PORT

print("=" * 50)
print("智能A股投资助手 V2")
print("=" * 50)
print(f"工作目录: {os.getcwd()}")
secret = os.environ.get('COOKIE_SECRET', '')
print(f"Cookie密钥: {'*' * len(secret) if secret else '未设置'}")
print(f"调试模式: {os.environ['DEBUG']}")
print(f"目标端口: {PORT}")
print("=" * 50)

print(f"\n检查端口 {PORT} 是否被占用...")
kill_port_process(PORT)
wait_for_port(PORT, timeout=2)
print("端口检查完成。\n")

# 先启动调度器（后台线程）
print("[启动] 正在启动定时任务调度器...")
scheduler_thread = threading.Thread(target=start_scheduler_in_background, daemon=True)
scheduler_thread.start()
print("[启动] 调度器启动中...\n")

# 启动主服务
try:
    from main import main
    main()
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有依赖已安装: pip install -r requirements.txt")
except Exception as e:
    print(f"启动错误: {e}")
    import traceback
    traceback.print_exc()

input("\n按回车键退出...")
