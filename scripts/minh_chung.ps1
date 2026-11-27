# In minh chung gon trong mot khung hinh de chup cho bao cao (cum nhom7xs, ho so XS).
# .\scripts\minh_chung.ps1 cai_dat tidb | ke_hoach tidb | ke_hoach mysql
param(
    [Parameter(Mandatory)][ValidateSet("cai_dat", "ke_hoach")][string]$Phan,
    [Parameter(Mandatory)][ValidateSet("tidb", "mysql")][string]$Engine
)
$ErrorActionPreference = "Stop"
$env:PROFILE = "XS"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $python = if (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    # Bat dung he can chup; he kia duoc tat de khong tranh tai nguyen.
    $running = & $python -W ignore -m bench.cli engine status
    $other = if ($Engine -eq "tidb") { "mysql" } else { "tidb" }
    if (-not ("$running" -like "*$Engine*" -and "$running" -notlike "*$other*")) {
        & $python -W ignore -m bench.cli engine $Engine --switch
        if ($LASTEXITCODE) { throw "Khong bat duoc $Engine" }
    }
    Clear-Host
    & $python -W ignore scripts/minh_chung.py $Phan $Engine
    if ($LASTEXITCODE) { throw "minh_chung.py that bai (ma $LASTEXITCODE)" }
} finally {
    Pop-Location
}
