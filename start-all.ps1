# To run this script if blocked by PowerShell execution policy, run:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Then execute: .\start-all.ps1

# Get the directory where the script is located
$scriptDir = $PSScriptRoot

# Determine the project path (idbi-wealth-engine folder)
if (Test-Path "$scriptDir\idbi-wealth-engine") {
    $projectPath = "$scriptDir\idbi-wealth-engine"
} else {
    $projectPath = $scriptDir
}

# PID file to track running services
$pidFile = "$scriptDir\.services.pid"

# Check if services are already running according to the PID file
if (Test-Path $pidFile) {
    try {
        $processes = Get-Content $pidFile | ConvertFrom-Json
        $running = @()
        foreach ($proc in $processes) {
            if (Get-Process -Id $proc.PID -ErrorAction SilentlyContinue) {
                $running += $proc
            }
        }
        if ($running.Count -gt 0) {
            Write-Host "Services are already running according to ${pidFile}:" -ForegroundColor Yellow
            foreach ($proc in $running) {
                Write-Host "  - $($proc.Name) (PID: $($proc.PID))" -ForegroundColor Yellow
            }
            Write-Host "Please stop them first using .\stop-all.ps1." -ForegroundColor Red
            exit
        }
    } catch {
        Write-Host "PID file was corrupted, cleaning up..." -ForegroundColor Yellow
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IDBI Wealth Engine - Full Stack Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for Python Virtual Environment inside the project path
$pythonCmd = "python"
$venvPath = "$projectPath\venv"
if (Test-Path "$venvPath\Scripts\python.exe") {
    $pythonCmd = "$venvPath\Scripts\python.exe"
    Write-Host "Found virtual environment. Using: $pythonCmd" -ForegroundColor Green
} else {
    Write-Host "No local virtual environment found. Using system Python." -ForegroundColor Yellow
}

# Check frontend dependencies
$frontendPath = "$projectPath\frontend"
if (-not (Test-Path "$frontendPath\node_modules")) {
    Write-Host "Frontend dependencies not found. Installing..." -ForegroundColor Yellow
    Start-Process cmd.exe -ArgumentList "/c npm install" -WorkingDirectory $frontendPath -Wait
}

# Start Backend (Listening on all interfaces via host 0.0.0.0)
Write-Host "Starting Backend API in a new window..." -ForegroundColor Cyan
$backendProc = Start-Process cmd.exe -ArgumentList "/k title IDBI Backend API && cd /d `"$projectPath`" && `"$pythonCmd`" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -PassThru

# Wait 3 seconds for backend to start up
Write-Host "Waiting for Backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Start Frontend (Exposed to the local network via --host flag)
Write-Host "Starting Frontend (Network-Exposed) in a new window..." -ForegroundColor Cyan
$frontendProc = Start-Process cmd.exe -ArgumentList "/k title IDBI Frontend && cd /d `"$frontendPath`" && npm run dev -- --host" -PassThru

# Save PIDs to file
$services = @(
    [PSCustomObject]@{ Name = "Backend"; PID = $backendProc.Id },
    [PSCustomObject]@{ Name = "Frontend"; PID = $frontendProc.Id }
)
$services | ConvertTo-Json | Out-File $pidFile -Encoding utf8

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Both servers have been launched!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Backend API : http://localhost:8000" -ForegroundColor White
Write-Host "API Docs    : http://localhost:8000/docs" -ForegroundColor White
Write-Host "Frontend    : http://localhost:3000 (Check the opened console window for Network IP)" -ForegroundColor White
Write-Host ""
Write-Host "To stop both servers, run: .\stop-all.ps1" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
