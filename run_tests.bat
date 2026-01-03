@echo off
echo ==========================================
echo  Running All Tests
echo ==========================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

echo [1/2] Running Backend Tests (pytest)
echo ------------------------------------------
cd backend
python -m pytest test_backend.py -v
set BACKEND_EXIT=%ERRORLEVEL%
cd ..

echo.
echo [2/2] Running Frontend Tests (vitest)
echo ------------------------------------------
cd frontend
call npm run test:run
set FRONTEND_EXIT=%ERRORLEVEL%
cd ..

echo.
echo ==========================================
echo  Test Results Summary
echo ==========================================

if %BACKEND_EXIT% EQU 0 (
    echo Backend Tests:  PASSED
) else (
    echo Backend Tests:  FAILED
)

if %FRONTEND_EXIT% EQU 0 (
    echo Frontend Tests: PASSED
) else (
    echo Frontend Tests: FAILED
)

echo ==========================================

if %BACKEND_EXIT% NEQ 0 exit /b %BACKEND_EXIT%
if %FRONTEND_EXIT% NEQ 0 exit /b %FRONTEND_EXIT%
exit /b 0
