@echo off
chcp 65001 >nul
echo ==============================================
echo   QQBot 启动中...
echo ==============================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [错误] 未检测到虚拟环境，请先运行 install.py
    echo   python install.py
    pause
    exit /b 1
)

echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [信息] 启动机器人...
python main.py

pause
