# To run this script if blocked by PowerShell execution policy, run:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# Then execute: .\stop-all.ps1

# Get the directory where the script is located
$scriptDir = $PSScriptRoot

# PID file to track running services
$pidFile = "$scriptDir\.services.pid"

if (-not (Test-Path $pidFile)) {
    Write-Host "No active service PID file found at $pidFile." -ForegroundColor Yellow
    Write-Host "If services are running, they were not started via start-all.ps1." -ForegroundColor Yellow
    exit
}

try {
    $processes = Get-Content $pidFile | ConvertFrom-Json
} catch {
    Write-Host "PID file was corrupted. Cleaning up." -ForegroundColor Red
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    exit
}

$stoppedCount = 0

foreach ($proc in $processes) {
    $targetPid = $proc.PID
    $name = $proc.Name
    
    if (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) {
        Write-Host "Stopping $name (PID: $targetPid)..." -ForegroundColor Cyan
        # Kill process tree starting from the parent cmd.exe
        taskkill /F /T /PID $targetPid 2>$null | Out-Null
        $stoppedCount++
    } else {
        Write-Host "$name (PID: $targetPid) is not running." -ForegroundColor Gray
    }
}

# Clean up PID file
Remove-Item $pidFile -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Stopped $stoppedCount service(s)." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
