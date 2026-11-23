# RQ4 chinh thuc: ca MySQL va TiDB, 64 luong, 84 luot. Bi ngat thi chay lai dung lenh nay.
param([int]$Duration=60, [int]$Reps=3, [int]$Rows=1000000, [string]$Output="results/rq4_official.csv", [string[]]$Indexes=@("0","1","3","5","sender_created","sender_cov"))
$ErrorActionPreference = "Stop"
$env:PROFILE = "XS"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $python = if ($env:PYTHON) { $env:PYTHON } elseif (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    function Invoke-Bench([string[]]$BenchArgs) {
        & $python -m bench.cli @BenchArgs
        if ($LASTEXITCODE) { throw "bench.cli $BenchArgs that bai (ma $LASTEXITCODE)" }
    }
    Invoke-Bench @("check")
    foreach ($engine in "mysql", "tidb") {
        Invoke-Bench @("engine", $engine, "--switch")
        Invoke-Bench @("load", $engine, "$Rows")
        # C3 chay truoc C1. C1 chi do 0 va 5 index.
        Invoke-Bench (@("rq4", $engine, "$Rows", "--seconds", "$Duration", "--reps", "$Reps", "--threads", "64", "--indexes") + $Indexes + @("--replicas", "3", "1", "--mode", "insert", "update", "--output", $Output))
    }
    Invoke-Bench @("engine", "stop")
} finally {
    Pop-Location
}
