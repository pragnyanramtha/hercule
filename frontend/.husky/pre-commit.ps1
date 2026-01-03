# Pre-commit hook for Windows (PowerShell)
# Runs tests only for changed files

Write-Host "🔍 Running pre-commit checks..." -ForegroundColor Cyan

# Get list of staged files
$stagedFiles = git diff --cached --name-only --diff-filter=ACM

# Check which areas changed
$backendChanged = $stagedFiles | Where-Object { $_ -match "^backend/" }
$frontendChanged = $stagedFiles | Where-Object { $_ -match "^(extension/|shared/)" }

$testsFailed = $false

# Run backend tests if backend files changed
if ($backendChanged) {
    Write-Host ""
    Write-Host "📦 Backend changes detected:" -ForegroundColor Yellow
    $backendChanged | ForEach-Object { Write-Host "   $_" }
    Write-Host ""
    Write-Host "🐍 Running backend tests (pytest)..." -ForegroundColor Cyan

    Push-Location backend
    & python -m pytest test_backend.py -v --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Backend tests failed" -ForegroundColor Red
        $testsFailed = $true
    } else {
        Write-Host "✅ Backend tests passed" -ForegroundColor Green
    }
    Pop-Location
} else {
    Write-Host "⏭️  No backend changes - skipping backend tests" -ForegroundColor Gray
}

# Run frontend tests if frontend files changed
if ($frontendChanged) {
    Write-Host ""
    Write-Host "📦 Frontend changes detected:" -ForegroundColor Yellow
    $frontendChanged | ForEach-Object { Write-Host "   $_" }
    Write-Host ""
    Write-Host "🧪 Running frontend tests (vitest)..." -ForegroundColor Cyan

    Push-Location extension

    # Type check first
    Write-Host "📝 Type checking..." -ForegroundColor Cyan
    & npm run type-check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ TypeScript type check failed" -ForegroundColor Red
        $testsFailed = $true
    } else {
        Write-Host "✅ Type check passed" -ForegroundColor Green

        # Run tests
        & npm run test:run
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Frontend tests failed" -ForegroundColor Red
            $testsFailed = $true
        } else {
            Write-Host "✅ Frontend tests passed" -ForegroundColor Green
        }
    }
    Pop-Location
} else {
    Write-Host "⏭️  No frontend changes - skipping frontend tests" -ForegroundColor Gray
}

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
if ($testsFailed) {
    Write-Host "❌ Some checks failed - commit aborted" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✅ All pre-commit checks passed!" -ForegroundColor Green
    exit 0
}
