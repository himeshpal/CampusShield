# CampusShield stack control - Docker only runs while you are working on the project.
#   .\scripts\stack.ps1 up              start Docker Desktop (if needed) + db, backend, lab
#   .\scripts\stack.ps1 up -Automation  same, plus n8n (needed from Phase 7)
#   .\scripts\stack.ps1 down            stop containers (data is kept) and shut Docker/WSL down to free RAM
#   .\scripts\stack.ps1 status          show container status and API health
param(
    [ValidateSet("up", "down", "status")][string]$Action = "status",
    [switch]$Automation
)

# Not "Stop": docker writes normal progress to stderr, which PowerShell 5.1 would treat as
# a fatal error. Failures are checked through $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
$env:Path = "D:\Docker\Program\resources\bin;$env:Path"

function Test-Docker {
    cmd /c "docker info >nul 2>&1"
    return $LASTEXITCODE -eq 0
}

function Wait-Docker {
    for ($i = 0; $i -lt 60; $i++) {
        if (Test-Docker) { return }
        Start-Sleep 3
    }
    throw "Docker engine did not start"
}

Push-Location $root
try {
    switch ($Action) {
        "up" {
            if (-not (Test-Docker)) {
                Write-Host "Starting Docker Desktop..."
                Start-Process "D:\Docker\Program\Docker Desktop.exe"
                Wait-Docker
            }
            if ($Automation) { docker compose --profile automation up -d } else { docker compose up -d }
            if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }
            Write-Host "`nAPI      http://localhost:8000/docs"
            if ($Automation) { Write-Host "n8n      http://localhost:5678" }
            Write-Host "Frontend cd frontend; npm run dev  ->  http://localhost:3000"
        }
        "down" {
            docker compose --profile automation stop
            Get-Process "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force
            wsl.exe --shutdown
            Write-Host "Stack stopped, Docker and WSL shut down (RAM released)."
        }
        "status" {
            docker compose --profile automation ps --format "table {{.Service}}\t{{.Status}}"
            try { Invoke-RestMethod http://localhost:8000/api/v1/health | Format-List } catch { Write-Host "API not reachable" }
        }
    }
} finally {
    Pop-Location
}
