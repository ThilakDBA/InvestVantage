[CmdletBinding()]
param([switch]$Build, [switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".env"))) {
    throw "Missing .env. Copy .env.example to .env and add your local credentials first."
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    $dockerBin = "C:\Program Files\Docker\Docker\resources\bin"
    if (Test-Path -LiteralPath (Join-Path $dockerBin "docker.exe")) {
        $env:Path = "$env:Path;$dockerBin"
    } else {
        throw "Docker CLI was not found. Install Docker Desktop or add docker.exe to PATH."
    }
}

function Test-DockerEngine {
    & docker info *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-DockerEngine)) {
    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path -LiteralPath $dockerDesktop)) {
        $dockerDesktop = Join-Path $env:LOCALAPPDATA "Programs\Docker\Docker\Docker Desktop.exe"
    }
    if (-not (Test-Path -LiteralPath $dockerDesktop)) {
        throw "Docker Desktop was not found. Start it manually and run this launcher again."
    }

    Write-Host "Starting Docker Desktop..."
    Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    $deadline = (Get-Date).AddMinutes(3)
    do {
        Start-Sleep -Seconds 3
        $ready = Test-DockerEngine
    } until ($ready -or (Get-Date) -ge $deadline)
    if (-not $ready) {
        throw "Docker did not become ready within three minutes. Open Docker Desktop to inspect it."
    }
}

Write-Host "Starting InvestVantage services..."
$composeArguments = @("compose", "up", "-d")
if ($Build) { $composeArguments += "--build" }
& docker @composeArguments
if ($LASTEXITCODE -ne 0) { throw "Docker Compose could not start InvestVantage." }

$apiUrl = "http://127.0.0.1:8000/health"
$dashboardHealthUrl = "http://127.0.0.1:8501/_stcore/health"
$dashboardUrl = "http://127.0.0.1:8501"
$deadline = (Get-Date).AddMinutes(2)
$apiReady = $false
$dashboardReady = $false
do {
    try {
        $apiReady = (Invoke-WebRequest -Uri $apiUrl -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200
    } catch { $apiReady = $false }
    try {
        $dashboardReady =
            (Invoke-WebRequest -Uri $dashboardHealthUrl -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200
    } catch { $dashboardReady = $false }
    if (-not ($apiReady -and $dashboardReady)) { Start-Sleep -Seconds 3 }
} until (($apiReady -and $dashboardReady) -or (Get-Date) -ge $deadline)

if (-not ($apiReady -and $dashboardReady)) {
    & docker compose ps
    throw "Services did not become healthy. Run: docker compose logs --tail 100"
}

Write-Host "InvestVantage is ready."
Write-Host "Dashboard: $dashboardUrl"
Write-Host "API docs:  http://127.0.0.1:8000/docs"
if (-not $NoBrowser) { Start-Process $dashboardUrl }
