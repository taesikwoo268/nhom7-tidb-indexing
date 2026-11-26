# RQ3: bien the khoa chinh tren ca MySQL va TiDB, database rieng logistics_rq3.
# Chay thu: .\scripts\rq3_official.ps1 -Rows 100000 -Reps 1 -Params 50 -Tag test
param([int]$Rows=1000000, [int]$Reps=3, [int]$Params=200, [string]$Tag="")
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
    $machine = if ($env:MACHINE_ID) { $env:MACHINE_ID } else { "M2" }
    $suffix = if ($Tag) { "_$Tag" } else { "" }
    $extra = @("--reps", "$Reps", "--params", "$Params",
        "--output", "results/rq3_$machine$suffix.csv",
        "--size-output", "results/rq3_size_$machine$suffix.csv")
    foreach ($engine in "mysql", "tidb") {
        Invoke-Python @("-m", "bench.cli", "engine", $engine, "--switch")
        Invoke-Python (@("-m", "experiments.rq3_pk", $engine, "$Rows") + $extra)
    }
    Invoke-Python @("-m", "bench.cli", "engine", "stop")
} finally {
    Pop-Location
}
