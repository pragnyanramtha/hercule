@echo off
echo ========================================
echo Privacy Policy Analyzer - Development Setup
echo ========================================
echo.

echo [1/4] Installing Python dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)
cd ..
echo Python dependencies installed successfully!
echo.

echo [2/4] Installing Node dependencies...
cd extension
call npm install
if %errorlevel% neq 0 (
    echo ERROR: Failed to install Node dependencies
    pause
    exit /b 1
)
cd ..
echo Node dependencies installed successfully!
echo.

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo To start the development environment:
echo   1. Start the backend:  cd backend ^&^& uvicorn main:app --reload --port 8000
echo   2. Start the extension: cd extension ^&^& npm run dev
echo.
echo NOTE: You need to run these commands in separate terminal windows.
echo.
echo IMPORTANT: Make sure to configure your .env file in the backend directory
echo            with your Azure OpenAI credentials before starting the backend.
echo.
pause
