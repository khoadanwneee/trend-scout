# Scrapes ITviec from this PC (GitHub's servers are blocked by ITviec), pushes the data to the
# repo, then triggers the GitHub workflow so the Telegram digest includes the new jobs.
#
# Runs inside a DEDICATED clone ($Sync), never in your development folder, because it does
# `git reset --hard origin/main` on every run.
#
# One-time setup:  .\scripts\setup-local-sync.ps1
param(
    [string]$Sync = "C:\My Workspace\My Project\trend-scout-sync",
    [string]$Repo = "khoadanwneee/trend-scout"
)
# git/python write progress to stderr; under "Stop" PowerShell 5.1 would abort on that.
$ErrorActionPreference = "Continue"
$log = Join-Path $Sync "sync.log"
function Log($m) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m" | Tee-Object -FilePath $log -Append }

Set-Location $Sync
$py = Join-Path $Sync "backend\.venv\Scripts\python.exe"
$env:PYTHONUTF8 = "1"
$pushed = $false

for ($attempt = 1; $attempt -le 3 -and -not $pushed; $attempt++) {
    Log "attempt $attempt: syncing with origin/main"
    git fetch origin main 2>&1 | Out-Null
    git reset --hard origin/main 2>&1 | Out-Null

    Push-Location backend
    Log "scraping itviec"
    & $py cli.py scrape itviec 2>&1 | ForEach-Object { Log $_ }
    & $py cli.py export 2>&1 | ForEach-Object { Log $_ }
    Pop-Location

    git add data/trend_scout.db frontend/public/data.json
    git diff --staged --quiet
    if ($LASTEXITCODE -eq 0) { Log "no changes to commit"; $pushed = $true; break }

    git -c user.name="trend-scout-local" -c user.email="trend-scout-local@users.noreply.github.com" commit -q -m "chore: ITviec data from local PC"
    git push origin HEAD:main 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -eq 0) {
        $pushed = $true
        Log "pushed"
        gh workflow run daily.yml --repo $Repo 2>&1 | ForEach-Object { Log "trigger: $_" }
    } else {
        Log "push rejected (the workflow probably pushed meanwhile); retrying from the latest origin/main"
    }
}
if (-not $pushed) { Log "FAILED after 3 attempts"; exit 1 }
Log "done"
