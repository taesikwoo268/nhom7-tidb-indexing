param([ValidateSet("tidb","mysql")][string]$Engine="tidb", [int]$Duration=60, [int]$Reps=3, [int]$Rows=1000000)
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $pythonCmd = if ($env:PYTHON) { $env:PYTHON } elseif (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    & $pythonCmd -m bench.cli rq4 $Engine $Rows --seconds $Duration --reps $Reps @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
