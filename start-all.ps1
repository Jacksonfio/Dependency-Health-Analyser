param(
    [switch]$Stop
)

$ROOT = "E:\sample\dep-health"

if ($Stop) {
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    Get-Job -Name "dephealth-*" -ErrorAction SilentlyContinue | Stop-Job | Remove-Job
    docker-compose -f "$ROOT\docker-compose.yml" down 2>$null
    Get-Process -Name "uvicorn", "node" -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "All services stopped." -ForegroundColor Green
    return
}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "     DepHealth - Starting All Services" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start databases with Docker
Write-Host "[1/4] Starting databases (PostgreSQL, Redis, Neo4j)..." -ForegroundColor Yellow
docker-compose -f "$ROOT\docker-compose.yml" up -d postgres redis neo4j
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker failed. Is Docker Desktop running?" -ForegroundColor Red
    exit 1
}
Write-Host "  Databases started." -ForegroundColor Green

# Wait for databases
Write-Host "  Waiting for databases to be ready..."
Start-Sleep -Seconds 10

# Step 2: Create .env if missing
if (-not (Test-Path "$ROOT\backend\.env")) {
    Write-Host "[2/4] Creating backend/.env from example..." -ForegroundColor Yellow
    Copy-Item "$ROOT\backend\.env.example" "$ROOT\backend\.env"
}

# Step 3: Start backend
Write-Host "[3/4] Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Yellow
$backendJob = Start-Job -Name "dephealth-backend" -ScriptBlock {
    param($dir)
    Set-Location $dir
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
} -ArgumentList "$ROOT\backend"
Write-Host "  Backend started (PID: $($backendJob.Id)). Waiting for it to be ready..."
Start-Sleep -Seconds 5

# Step 4: Start frontend
Write-Host "[4/4] Starting Next.js frontend on http://localhost:3000 ..." -ForegroundColor Yellow
$frontendJob = Start-Job -Name "dephealth-frontend" -ScriptBlock {
    param($dir)
    Set-Location $dir
    npm run dev
} -ArgumentList "$ROOT\frontend"

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  All services starting!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Neo4j:     http://localhost:7474 (neo4j/password)" -ForegroundColor White
Write-Host "  Flower:    http://localhost:5555" -ForegroundColor White
Write-Host ""
Write-Host "  To view backend logs:  Receive-Job -Name 'dephealth-backend'" -ForegroundColor Gray
Write-Host "  To view frontend logs: Receive-Job -Name 'dephealth-frontend'" -ForegroundColor Gray
Write-Host "  To stop everything:     .\start-all.ps1 -Stop" -ForegroundColor Gray
Write-Host ""
