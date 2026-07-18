Write-Host "Starting DepHealth..."

$backend = Start-Job -ScriptBlock {
    Set-Location "E:\sample\dep-health\backend"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

$frontend = Start-Job -ScriptBlock {
    Set-Location "E:\sample\dep-health\frontend"
    npm run dev
}

Write-Host "Backend:  http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
Write-Host ""
Write-Host "To view logs: Get-Job | Receive-Job"
Write-Host "To stop:      Get-Job | Stop-Job"
