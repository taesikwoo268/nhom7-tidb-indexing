param([ValidateSet("tidb","mysql","status","stop")][string]$Engine, [switch]$Switch, [switch]$Status, [switch]$Stop)
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $pythonCmd = if ($env:PYTHON) { $env:PYTHON } elseif (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    if ($Status) { $Engine = "status" }
    if ($Stop) { $Engine = "stop" }
    $cliArgs = @("engine", $Engine)
    if ($Switch) { $cliArgs += "--switch" }
    & $pythonCmd -m bench.cli @cliArgs
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
