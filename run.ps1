# Single-command dev launcher for StudyHelp.
# Starts postgres+redis+api via docker compose, runs pending migrations,
# installs frontend deps if needed, then starts the Vite dev server in the foreground.
# Ctrl+C stops the frontend; run `docker compose down` separately to stop backend services.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "backend\.env")) {
    Write-Host "backend\.env missing — copying from .env.example" -ForegroundColor Yellow
    Copy-Item "backend\.env.example" "backend\.env"
}

Write-Host "Starting postgres, redis, api (docker compose)..." -ForegroundColor Cyan
docker compose up -d --build postgres redis api

Write-Host "Waiting for api container to be healthy..." -ForegroundColor Cyan
$maxWait = 60
$elapsed = 0
while ($true) {
    $status = docker inspect --format "{{.State.Health.Status}}" studyhelp-postgres-1 2>$null
    if ($status -eq "healthy") { break }
    if ($elapsed -ge $maxWait) { throw "postgres did not become healthy in time" }
    Start-Sleep -Seconds 2
    $elapsed += 2
}

Write-Host "Running alembic migrations..." -ForegroundColor Cyan
docker compose exec -T api alembic upgrade head

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location frontend
    npm install
    Pop-Location
}

Write-Host ""
Write-Host "Backend API:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend:     http://localhost:5173" -ForegroundColor Green
Write-Host "Starting frontend dev server (Ctrl+C to stop)..." -ForegroundColor Cyan
Push-Location frontend
npm run dev
Pop-Location
