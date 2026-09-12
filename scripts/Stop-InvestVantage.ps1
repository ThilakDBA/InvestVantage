[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found."
}

Write-Host "Stopping InvestVantage services..."
& docker compose down
if ($LASTEXITCODE -ne 0) { throw "Docker Compose could not stop InvestVantage cleanly." }
Write-Host "InvestVantage stopped. PostgreSQL data was preserved."
