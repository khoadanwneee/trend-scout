# One-time setup: dedicated clone + venv + a daily Windows scheduled task.
# Usage:  .\scripts\setup-local-sync.ps1 [-At "07:30"]
param(
    [string]$Sync = "C:\My Workspace\My Project\trend-scout-sync",
    [string]$Repo = "khoadanwneee/trend-scout",
    [string]$At = "07:30"
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $Sync ".git"))) {
    git clone "https://github.com/$Repo.git" $Sync
}
$py = Join-Path $Sync "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Push-Location (Join-Path $Sync "backend")
    python -m venv .venv
    & ".\.venv\Scripts\python.exe" -m pip install -q -r requirements.txt
    Pop-Location
}

$script = Join-Path $Sync "scripts\local-itviec.ps1"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`" -Sync `"$Sync`" -Repo `"$Repo`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
# StartWhenAvailable: if the PC was off at $At, run as soon as it is back on.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -RunOnlyIfNetworkAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
Register-ScheduledTask -TaskName "TrendScout-ITviec" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Scrape ITviec from this PC and push to GitHub" -Force | Out-Null
Write-Host "Task 'TrendScout-ITviec' registered: daily at $At."
