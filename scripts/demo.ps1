# Demo cho bao cao. Chay tren project Docker rieng (nhom7demo), ho so XS.
# .\scripts\demo.ps1 bat_tidb | bat_mysql | co_ban_mysql | co_ban_tidb | chiu_loi_tidb | chiu_loi_mysql | them_node | trang_thai | dung | don
param([Parameter(Mandatory)][ValidateSet("bat_tidb","bat_mysql","co_ban_mysql","co_ban_tidb","chiu_loi_tidb","chiu_loi_mysql","them_node","trang_thai","dung","don")][string]$Phan)
$ErrorActionPreference = "Stop"
$old = @{ PROFILE = $env:PROFILE; COMPOSE_PROJECT_NAME = $env:COMPOSE_PROJECT_NAME; PYTHONIOENCODING = $env:PYTHONIOENCODING }
$env:PROFILE = "XS"
$env:COMPOSE_PROJECT_NAME = "nhom7demo"
$env:PYTHONIOENCODING = "utf-8"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    $python = if (Test-Path .venv/Scripts/python.exe) { ".venv/Scripts/python.exe" } else { "python" }
    function Invoke-Python([string[]]$PyArgs) {
        & $python -W ignore @PyArgs
        if ($LASTEXITCODE) { throw "python $PyArgs that bai (ma $LASTEXITCODE)" }
    }
    # He da chay thi dung luon, khong tao lai va khong can Internet.
    function Start-Engine([string]$Engine) {
        $running = & $python -W ignore -m bench.cli engine status
        $other = if ($Engine -eq "tidb") { "mysql" } else { "tidb" }
        if ("$running" -like "*$Engine*" -and "$running" -notlike "*$other*") { return }
        # tikv4 chi co sau demo them node. Dung truoc khi chuyen he.
        if ($Engine -eq "mysql") { docker compose -f docker/tidb.compose.yml -f docker/tikv4-demo.yml stop tikv4 }
        Invoke-Python @("-m", "bench.cli", "engine", $Engine, "--switch")
    }
    switch ($Phan) {
        "bat_tidb"       { Start-Engine tidb }
        "bat_mysql"      { Start-Engine mysql }
        "co_ban_mysql"   { Start-Engine mysql; Invoke-Python @("scripts/demo_co_ban.py", "mysql") }
        "co_ban_tidb"    { Start-Engine tidb; Invoke-Python @("scripts/demo_co_ban.py", "tidb") }
        "chiu_loi_tidb"  { Start-Engine tidb; Invoke-Python @("scripts/demo_mo_rong.py", "chiu_loi", "tidb") }
        "chiu_loi_mysql" { Start-Engine mysql; Invoke-Python @("scripts/demo_mo_rong.py", "chiu_loi", "mysql") }
        "them_node"      { Start-Engine tidb; Invoke-Python @("scripts/demo_mo_rong.py", "them_node") }
        "trang_thai"     { Invoke-Python @("-m", "bench.cli", "engine", "status") }
        "dung" {
            Invoke-Python @("-m", "bench.cli", "engine", "stop")
            docker compose -f docker/tidb.compose.yml -f docker/tikv4-demo.yml stop tikv4
        }
        "don" {
            # Chi xoa container va volume cua project demo.
            docker compose -f docker/mysql.compose.yml -f docker/tidb.compose.yml -f docker/tikv4-demo.yml down -v
        }
    }
} finally {
    $env:PROFILE = $old.PROFILE
    $env:COMPOSE_PROJECT_NAME = $old.COMPOSE_PROJECT_NAME
    $env:PYTHONIOENCODING = $old.PYTHONIOENCODING
    Pop-Location
}
