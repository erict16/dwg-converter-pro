$ErrorActionPreference = "Stop"
$nodeBin = "C:\Users\TYM\tools\node\node-v24.18.0-win-x64"
if (Test-Path $nodeBin) { $env:Path = "$nodeBin;" + $env:Path }
Set-Location "$PSScriptRoot\..\apps\web"
if (-not (Test-Path .\node_modules)) { npm install }
if (-not (Test-Path .\.env.local)) {
  Copy-Item .\.env.example .\.env.local -ErrorAction SilentlyContinue
}
Write-Host "Web → http://localhost:3000"
npm run dev
