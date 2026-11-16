# Starts backend (http://127.0.0.1:8000) and frontend (http://localhost:3000) in two windows.
$root = $PSScriptRoot
$py = Join-Path $root "backend\.venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Host "Creating Python venv..."
    Push-Location (Join-Path $root "backend")
    python -m venv .venv
    & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
    Pop-Location
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules\next"))) {
    Write-Host "Installing frontend packages..."
    Push-Location (Join-Path $root "frontend"); npm install; Pop-Location
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev"
Write-Host "Backend:  http://127.0.0.1:8000/docs"
Write-Host "Frontend: http://localhost:3000"
