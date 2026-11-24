# RQ1 chinh thuc: ca MySQL va TiDB. Bi ngat thi chay lai dung lenh nay.
param([int]$Rows=1000000, [int]$Reps=5, [int]$Params=200, [string]$Output="")
$ErrorActionPreference = "Stop"
$env:PROFILE = "XS"
# Moi quy mo dung mot database rieng, nen khong phai xoa du lieu cu.
$env:DB_NAME = if ($Rows -eq 1000000) { "logistics" } else { "logistics_$Rows" }
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $python = if ($env:PYTHON) { $env:PYTHON } elseif (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    function Invoke-Python([string[]]$PyArgs) {
        & $python @PyArgs
        if ($LASTEXITCODE) { throw "python $PyArgs that bai (ma $LASTEXITCODE)" }
    }
    Invoke-Python @("-m", "bench.cli", "check")
    $extra = @("--reps", "$Reps", "--params", "$Params")
    if ($Output) { $extra += @("--output", $Output) }
    foreach ($engine in "mysql", "tidb") {
        Invoke-Python @("-m", "bench.cli", "engine", $engine, "--switch")
        Invoke-Python @("-m", "bench.cli", "load", $engine, "$Rows")
        Invoke-Python (@("-m", "experiments.rq1_covering", $engine, "$Rows") + $extra)
    }
    Invoke-Python @("-m", "bench.cli", "engine", "stop")
} finally {
    Pop-Location
}
