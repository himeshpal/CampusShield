# CampusShield stack control - Docker only runs while you are working on the project.
#   .\scripts\stack.ps1 up              start Docker Desktop (if needed) + db, backend, lab
#   .\scripts\stack.ps1 up -Automation  same, plus n8n + Mailpit (alert delivery, scheduled scans)
#   .\scripts\stack.ps1 up -Siem        same, plus the Wazuh manager (~1 GB RAM; can be combined)
#   .\scripts\stack.ps1 down            stop containers (data is kept) and shut Docker/WSL down to free RAM
#   .\scripts\stack.ps1 status          show container status and API health
param(
    [ValidateSet("up", "down", "status")][string]$Action = "status",
    [switch]$Automation,
    [switch]$Siem
)

# Not "Stop": docker writes normal progress to stderr, which PowerShell 5.1 would treat as
# a fatal error. Failures are checked through $LASTEXITCODE instead.
$ErrorActionPreference = "Continue"
$root = Split-Path $PSScriptRoot -Parent
# Docker Desktop: the default install location, or a custom one (e.g. D:\Docker\Program)
$dockerHome = @("$env:ProgramFiles\Docker\Docker", "D:\Docker\Program") |
    Where-Object { Test-Path (Join-Path $_ "Docker Desktop.exe") } | Select-Object -First 1
if ($dockerHome) { $env:Path = "$dockerHome\resources\bin;$env:Path" }

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
                if (-not $dockerHome) { throw "Docker Desktop not found: install it or start it manually" }
                Start-Process (Join-Path $dockerHome "Docker Desktop.exe")
                Wait-Docker
            }
            $profiles = @()
            if ($Automation) { $profiles += "--profile", "automation" }
            if ($Siem) { $profiles += "--profile", "siem" }
            docker compose @profiles up -d
            if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }
            Write-Host "`nAPI      http://127.0.0.1:8000/docs"
            if ($Automation) {
                Write-Host "n8n      http://127.0.0.1:5678"
                Write-Host "Mailpit  http://127.0.0.1:8025  (alert e-mails)"
            }
            if ($Siem) { Write-Host "Wazuh    manager on 172.25.0.4, agent on lab-pc-01 (alerts appear in CampusShield)" }
            Write-Host "Frontend cd frontend; npm run dev  ->  http://localhost:3000"
        }
        "down" {
            docker compose --profile automation --profile siem stop
            Get-Process "Docker Desktop" -ErrorAction SilentlyContinue | Stop-Process -Force
            wsl.exe --shutdown
            Write-Host "Stack stopped, Docker and WSL shut down (RAM released)."
        }
        "status" {
            docker compose --profile automation --profile siem ps --format "table {{.Service}}\t{{.Status}}"
            try { Invoke-RestMethod http://127.0.0.1:8000/api/v1/health | Format-List } catch { Write-Host "API not reachable" }
        }
    }
} finally {
    Pop-Location
}
