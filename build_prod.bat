@echo off
chcp 65001 >nul
echo ================================================
echo   智能A股投资助手 V2 - 生产构建脚本
echo ================================================
echo.

cd /d "%~dp0"

echo [1/4] 检查依赖...
echo.

echo [2/4] 构建前端...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo 前端构建失败！
    pause
    exit /b 1
)
cd ..

echo.
echo [3/4] 复制静态文件到后端...
if exist frontend\dist\index.html (
    xcopy /E /I /Y frontend\dist\* backend\static\
    echo 静态文件复制完成
) else (
    echo 错误：frontend\dist\index.html 不存在
    pause
    exit /b 1
)

echo.
echo [4/4] 安装Python生产依赖...
pip install gunicorn -q

echo.
echo ================================================
echo   构建完成！
echo ================================================
echo.
echo 生产模式启动命令：
echo   cd backend
echo   set COOKIE_SECRET=your-strong-secret-here
echo   set DEBUG=False
echo   gunicorn -w 4 -b 0.0.0.0:5001 main:app
echo.
pause
