param([int]$Port = 8001)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install the environment using README.md first.' }
$env:SEBI_DB = 'runtime/research.sqlite'
& $python -m uvicorn sebi_engine.api:app --host 127.0.0.1 --port $Port
