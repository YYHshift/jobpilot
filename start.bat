@echo off
echo ==========================================
echo       🚀 Starting JobPilot System...
echo ==========================================

:: 1. 启动后端 (在新窗口中)
:: 注意：这里假设你的虚拟环境文件夹叫 venv
start "JobPilot Backend" cmd /k "cd backend && call venv\Scripts\activate && uvicorn main:app --reload"

:: 等待 2 秒，让后端先跑起来
timeout /t 2 /nobreak >nul

:: 2. 启动前端 (在新窗口中)
start "JobPilot Frontend" cmd /k "cd frontend && npm run dev"

:: 3. 自动打开浏览器
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo ==========================================
echo       ✅ System Online! Have Fun!
echo ==========================================