# B.1: dung luong bang va chi muc o 1 va 3 trieu dong, ca MySQL va TiDB.
# Database rieng logistics_b1. Sau khi do, chay mo hinh tu file du lieu.
param([string]$Output="")
$ErrorActionPreference = "Stop"
$env:PROFILE = "XS"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $python = if ($env:PYTHON) { $env:PYTHON } elseif (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    function Invoke-Python([string[]]$PyArgs) {
        & $python @PyArgs
        if ($LASTEXITCODE) { throw "python $PyArgs that bai (ma $LASTEXITCODE)" }
    }
    Invoke-Python @("-m", "bench.cli", "check")
    $extra = if ($Output) { @("--output", $Output) } else { @() }
    foreach ($engine in "mysql", "tidb") {
        Invoke-Python @("-m", "bench.cli", "engine", $engine, "--switch")
        Invoke-Python (@("-m", "experiments.b1_storage", $engine) + $extra)
    }
    Invoke-Python @("-m", "bench.cli", "engine", "stop")
    Invoke-Python @("-m", "experiments.b1_model")
} finally {
    Pop-Location
}
