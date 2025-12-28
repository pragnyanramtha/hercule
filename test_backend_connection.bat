@echo off
echo ========================================
echo Testing Backend Connection
echo ========================================
echo.

echo Testing health endpoint...
curl -s http://localhost:8000/health
if %errorlevel% neq 0 (
    echo.
    echo ❌ Backend is not responding
    echo    Make sure the backend is running: cd backend ^&^& uvicorn main:app --reload --port 8000
) else (
    echo.
    echo ✅ Backend is running and responding
)
echo.

echo ========================================
echo.
pause
