# Postgres 17 portable para los tests en Windows, sin instalar nada.
# La primera vez baja los binarios de EDB (unos 390 MB) a .postgres\, que git ignora.
# Solo escucha en localhost, en el puerto 54317, con autenticación trust:
# es una base de prueba vacía, nunca datos reales.
#
# Uso:
#   scripts\postgres-local.ps1 levantar
#   scripts\postgres-local.ps1 bajar

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("levantar", "bajar")]
    [string]$Accion
)

$ErrorActionPreference = "Stop"

$Version = "17.12-1"
$Puerto = 54317
$Raiz = Split-Path -Parent $PSScriptRoot
$Carpeta = Join-Path $Raiz ".postgres"
$Bin = Join-Path $Carpeta "pgsql\bin"
$Datos = Join-Path $Carpeta "datos"
$Log = Join-Path $Carpeta "postgres.log"

function Get-Binarios {
    if (Test-Path (Join-Path $Bin "pg_ctl.exe")) { return }
    New-Item -ItemType Directory -Force $Carpeta | Out-Null
    $Zip = Join-Path $Carpeta "postgresql-$Version-windows-x64-binaries.zip"
    if (-not (Test-Path $Zip)) {
        $Url = "https://get.enterprisedb.com/postgresql/postgresql-$Version-windows-x64-binaries.zip"
        Write-Host "Bajando Postgres $Version (una sola vez)..."
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri $Url -OutFile $Zip
    }
    Write-Host "Descomprimiendo..."
    Expand-Archive -Path $Zip -DestinationPath $Carpeta -Force
    Remove-Item $Zip
}

if ($Accion -eq "levantar") {
    Get-Binarios
    if (-not (Test-Path (Join-Path $Datos "PG_VERSION"))) {
        & (Join-Path $Bin "initdb.exe") -D $Datos -U postgres -A trust -E UTF8 --no-locale | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "initdb falló" }
    }
    & (Join-Path $Bin "pg_ctl.exe") -D $Datos -l $Log -o "-p $Puerto -c listen_addresses=localhost" -w start
    if ($LASTEXITCODE -ne 0) { throw "No arrancó. Mirá $Log" }
    Write-Host "Postgres de prueba en postgresql://postgres@localhost:$Puerto/postgres"
}
else {
    & (Join-Path $Bin "pg_ctl.exe") -D $Datos -m fast -w stop
}
