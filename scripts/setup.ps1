# SIGNAL Development Setup Script
# Run from the root: .\scripts\setup.ps1

Write-Host "Setting up SIGNAL development environment..." -ForegroundColor Cyan

# Backend
Write-Host "`n[1/3] Setting up backend..." -ForegroundColor Yellow
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  Created backend/.env — fill in your credentials" -ForegroundColor Green
}
Set-Location ..

# Frontend
Write-Host "`n[2/3] Setting up frontend..." -ForegroundColor Yellow
Set-Location frontend
npm install
if (-not (Test-Path ".env.local")) {
    Copy-Item ".env.local.example" ".env.local"
    Write-Host "  Created frontend/.env.local — fill in your credentials" -ForegroundColor Green
}
Set-Location ..

# Database
Write-Host "`n[3/3] Database migrations..." -ForegroundColor Yellow
Write-Host "  Run manually: psql `$DATABASE_URL -f database/migrations/001_initial_schema.sql"
Write-Host "  Then seed:    psql `$DATABASE_URL -f database/seeds/role_templates.sql"

Write-Host "`nSetup complete." -ForegroundColor Cyan
Write-Host "Start backend: cd backend && .\.venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload"
Write-Host "Start frontend: cd frontend && npm run dev"
