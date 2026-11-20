param([Parameter(Mandatory)][ValidateSet("mysql","tidb")][string]$Engine, [int]$Rows=1000000, [int]$Seed=20261116)
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $pythonCmd = if ($env:PYTHON) { $env:PYTHON } elseif (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    & $pythonCmd -m bench.cli load $Engine $Rows $Seed
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
