@echo off
echo ========================================
echo Privacy Policy Analyzer - Setup Verification
echo ========================================
echo.

echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found. Please install Python 3.11+
    goto :error
) else (
    python --version
    echo ✅ Python is installed
)
echo.

echo [2/6] Checking Node.js installation...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js not found. Please install Node.js 18+
    goto :error
) else (
    node --version
    echo ✅ Node.js is installed
)
echo.

echo [3/6] Checking backend .env file...
if exist backend\.env (
    echo ✅ backend\.env file exists
) else (
    echo ❌ backend\.env file NOT found
    echo    Please create it from .env.example and add your Azure OpenAI credentials
    goto :error
)
echo.

echo [4/6] Checking Python dependencies...
cd backend
pip show fastapi >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python dependencies not installed
    echo    Run: pip install -r requirements.txt
    cd ..
    goto :error
) else (
    echo ✅ Python dependencies appear to be installed
)
cd ..
echo.

echo [5/6] Checking Node dependencies...
if exist extension\node_modules (
    echo ✅ Node dependencies appear to be installed
) else (
    echo ❌ Node dependencies not installed
    echo    Run: cd extension ^&^& npm install
    goto :error
)
echo.

echo [6/6] Checking extension build...
if exist extension\dist (
    echo ✅ Extension dist folder exists
) else (
    echo ⚠️  Extension not built yet
    echo    Run: cd extension ^&^& npm run dev
)
echo.

echo ========================================
echo ✅ Setup verification complete!
echo ========================================
echo.
echo You are ready to start manual testing.
echo Please follow the instructions in MANUAL_TEST_GUIDE.md
echo.
goto :end

:error
echo.
echo ========================================
echo ❌ Setup verification failed
echo ========================================
echo.
echo Please fix the issues above before proceeding with testing.
echo Refer to README.md for setup instructions.
echo.

:end
pause
