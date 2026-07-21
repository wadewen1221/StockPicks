@echo off
chcp 65001 >nul
echo ================================================
echo   智能A股投资助手 V2 - 生产模式启动
echo ================================================
echo.

cd /d "%~dp0"

:: ========== 生产配置（请修改以下值）==========

:: Cookie密钥 - 生产环境必须修改为强随机字符串
:: 推荐使用：https://www.random.org/ 生成
set COOKIE_SECRET=CHANGE_THIS_TO_A_STRONG_RANDOM_SECRET

:: 允许的来源 - 生产环境配置你的域名
set ALLOWED_ORIGINS=https://your-domain.com

:: 关闭调试模式
set DEBUG=False

:: ========== 生产配置结束 ==========

echo 当前配置：
echo   Cookie密钥: %COOKIE_SECRET:~0,10%...
echo   调试模式: %DEBUG%
echo   允许来源: %ALLOWED_ORIGINS%
echo.

:: 检查 gunicorn 是否安装
python -c "import gunicorn" 2>nul
if %errorlevel% neq 0 (
    echo 错误：gunicorn 未安装
    echo 请运行：pip install gunicorn
    pause
    exit /b 1
)

echo 启动服务...
echo.
echo 访问地址：http://localhost:5001
echo 按 Ctrl+C 停止服务
echo.

:: 使用 gunicorn 启动（4个工作进程）
gunicorn -w 4 -b 0.0.0.0:5001 main:app

pause
