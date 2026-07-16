$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\services\worker"
if (-not (Test-Path .\.venv\Scripts\uvicorn.exe)) {
  python -m venv .venv
  .\.venv\Scripts\pip.exe install -r requirements.txt
}
Write-Host "Worker → http://127.0.0.1:8000"
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
