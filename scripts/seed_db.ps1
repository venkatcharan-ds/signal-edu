# SIGNAL EDU — database seeder
#
# Option A — pure SQL via psql (fastest, no Python runtime needed):
#   ./scripts/seed_db.ps1 -Method sql
#
# Option B — Python async seeder (uses the same code path as startup):
#   ./scripts/seed_db.ps1 -Method python
#
# In both cases DATABASE_URL must be set in the environment or passed as -DatabaseUrl.

param(
    [string]$DatabaseUrl = $env:DATABASE_URL,
    [ValidateSet("sql", "python")]
    [string]$Method = "python"
)

if (-not $DatabaseUrl) {
    Write-Error "Set DATABASE_URL environment variable or pass -DatabaseUrl"
    exit 1
}

if ($Method -eq "sql") {
    Write-Host "Seeding role templates via psql..." -ForegroundColor Yellow
    $env:DATABASE_URL = $DatabaseUrl
    psql $DatabaseUrl -f database/seeds/role_templates.sql
    Write-Host "Done." -ForegroundColor Green
}
else {
    Write-Host "Seeding role templates via Python seeder..." -ForegroundColor Yellow
    Push-Location backend
    try {
        $env:DATABASE_URL = $DatabaseUrl
        python scripts/seed_roles.py
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Seed script exited with code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
    Write-Host "Done." -ForegroundColor Green
}
