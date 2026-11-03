param(
    [int]$Port = 3407,
    [string]$DataDir = "D:\aWusheng\mysql-data"
)

$exe = "C:\Program Files\MySQL\MySQL Server 9.4\bin\mysqld.exe"
if (-not (Test-Path $exe)) {
    throw "mysqld.exe not found: $exe"
}
if (-not (Test-Path $DataDir)) {
    throw "MySQL data directory not found: $DataDir"
}

$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listening) {
    Write-Output "MySQL already listening on $Port (PID $($listening.OwningProcess))"
    exit 0
}

$log = Join-Path $DataDir "start.log"
Start-Process -FilePath $exe -ArgumentList @(
    "--no-defaults",
    "--datadir=$DataDir",
    "--port=$Port",
    "--bind-address=127.0.0.1",
    "--log-error=$log"
) -WindowStyle Hidden

Start-Sleep -Seconds 5
$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    Get-Content $log -Tail 40 -ErrorAction SilentlyContinue
    throw "MySQL failed to start on $Port"
}
Write-Output "MySQL listening on $Port"
