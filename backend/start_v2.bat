@echo off
chcp 65001 >nul
REM 智能A股投资助手 V2 启动脚本

REM 设置Cookie密钥（生产环境请修改为强随机字符串）
set COOKIE_SECRET=StockPicks-secret-2026

REM 允许的来源（开发模式用*，生产环境请配置具体域名）
set ALLOWED_ORIGINS=*

REM 调试模式
set DEBUG=True

REM 启动服务
echo Starting V2 server...
python main.py

pause
