param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Install the environment using README.md first.' }
& $python -m sebi_engine.cli --db runtime/demo.sqlite demo
if ($LASTEXITCODE -ne 0) { throw 'Demo initialization failed.' }
$env:SEBI_DB = 'runtime/demo.sqlite'
& $python -m uvicorn sebi_engine.api:app --host 127.0.0.1 --port $Port
