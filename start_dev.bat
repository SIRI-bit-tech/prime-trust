@echo off
setlocal enabledelayedexpansion

REM PrimeTrust Banking Application - Development Startup Script (Windows)
REM This script starts the development server with all necessary setup

echo ============================================================
echo 🎯 PrimeTrust Banking Application - Development Setup
echo ============================================================

REM Install dependencies
echo [INFO] 📦 Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed

REM Create necessary directories
echo [INFO] 📁 Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "media" mkdir media
if not exist "staticfiles" mkdir staticfiles
echo [SUCCESS] Directories created

REM Run database migrations
echo [INFO] 🗄️ Running database migrations...
python manage.py migrate
if errorlevel 1 (
    echo [ERROR] Database migrations failed
    pause
    exit /b 1
)
echo [SUCCESS] Database migrations completed

REM Create cache tables
echo [INFO] 🔄 Creating cache tables...
python manage.py createcachetable
echo [SUCCESS] Cache tables ready

REM Collect static files
echo [INFO] 📄 Collecting static files...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo [WARNING] Static file collection failed, but continuing...
)
echo [SUCCESS] Static files collected

echo [SUCCESS] ✅ Development setup completed!

REM Start development server
echo [INFO] 🚀 Starting development server...
echo [INFO] 🌟 PrimeTrust Banking Application (Development Mode)
echo [INFO] 🌐 Server will be available at: http://localhost:8000
echo [INFO] 📊 API Documentation: http://localhost:8000/api/docs/
echo [INFO] 🔧 Admin Panel: http://localhost:8000/admin/
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Django development server
python manage.py runserver 0.0.0.0:8000

pause 