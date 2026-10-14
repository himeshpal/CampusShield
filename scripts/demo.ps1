# CampusShield demo helper: make changes on the lab network, then scan to see the alerts.
#   .\scripts\demo.ps1 open-port     switch Telnet on at the lab PC (.20)  -> "port opened", "risk rose"
#   .\scripts\demo.ps1 close-port    switch it off again                   -> the alert resolves itself
#   .\scripts\demo.ps1 unplug        power off the Wi-Fi AP (.30)          -> "did not respond"
#   .\scripts\demo.ps1 plug          power it on again                     -> the alert resolves itself
#   .\scripts\demo.ps1 scan          start a standard scan the way n8n does (-Profile quick|standard|deep)
#   .\scripts\demo.ps1 reset         undo every change above
param(
    [Parameter(Mandatory)][ValidateSet("open-port", "close-port", "unplug", "plug", "scan", "reset")]
    [string]$Action,
    [ValidateSet("quick", "standard", "deep")][string]$Profile = "standard"
)

$ErrorActionPreference = "Continue"  # docker writes progress to stderr
$root = Split-Path $PSScriptRoot -Parent
$env:Path = "D:\Docker\Program\resources\bin;$env:Path"

function Get-EnvValue([string]$name) {
    $line = Get-Content (Join-Path $root ".env") | Where-Object { $_ -match "^$name=" } | Select-Object -First 1
    if (-not $line) { throw "$name is not set in .env" }
    return $line.Substring($name.Length + 1)
}

function Stop-Telnet {
    docker compose exec -T lab-pc-01 sh -c "pkill telnetd; true" | Out-Null
}

Push-Location $root
try {
    switch ($Action) {
        "open-port" {
            docker compose exec -T lab-pc-01 sh -c "pgrep telnetd >/dev/null || telnetd -p 23 -l /bin/login"
            Write-Host "Telnet (23/tcp) is now open on lab-pc-01 (172.25.0.20). Run a scan to see the alert."
        }
        "close-port" {
            Stop-Telnet
            Write-Host "Telnet closed on lab-pc-01. The next scan resolves the 'port opened' alert."
        }
        "unplug" {
            docker compose stop wifi-ap | Out-Null
            Write-Host "Wi-Fi AP (172.25.0.30) is off. Run a scan to see the 'did not respond' alert."
        }
        "plug" {
            docker compose start wifi-ap | Out-Null
            Write-Host "Wi-Fi AP is back. The next scan resolves the alert."
        }
        "scan" {
            $headers = @{ "X-API-Key" = (Get-EnvValue "SERVICE_API_KEY") }
            $body = @{ profile = $Profile } | ConvertTo-Json
            $scan = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/automation/scans" `
                -Headers $headers -Body $body -ContentType "application/json"
            Write-Host "Scan #$($scan.id) ($Profile) started. Watch it on http://localhost:3000/scans"
        }
        "reset" {
            Stop-Telnet
            docker compose start wifi-ap | Out-Null
            Write-Host "Lab back to its normal state (Telnet off, Wi-Fi AP on)."
        }
    }
} finally {
    Pop-Location
}
