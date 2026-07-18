@echo off
cd /d "E:\sample\dep-health"

echo ============================================
echo     DepHealth - Starting All Services
echo ============================================
echo.

:: Start databases
echo [1/4] Starting databases (PostgreSQL, Redis, Neo4j)...
docker-compose up -d postgres redis neo4j
if %errorlevel% neq 0 (
    echo Docker failed. Is Docker Desktop running?
    pause
    exit /b 1
)
echo   Databases started.
echo   Waiting 10s for databases to be ready...
timeout /t 10 /nobreak >nul

:: Create .env if missing
if not exist "backend\.env" (
    echo [2/4] Creating backend\.env from example...
    copy "backend\.env.example" "backend\.env" >nul
)

:: Start backend
echo [3/4] Starting FastAPI backend on http://localhost:8000 ...
start "DepHealth-Backend" cmd /c "cd /d "%~dp0backend" && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo   Backend starting...
timeout /t 5 /nobreak >nul

:: Start frontend
echo [4/4] Starting Next.js frontend on http://localhost:3000 ...
start "DepHealth-Frontend" cmd /c "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ============================================
echo  All services starting!
echo ============================================
echo.
echo  Frontend:  http://localhost:3000
echo  Backend:   http://localhost:8000
echo  API Docs:  http://localhost:8000/docs
echo  Neo4j:     http://localhost:7474 (neo4j/password)
echo.
echo  Close the windows to stop services.
echo.

pause
