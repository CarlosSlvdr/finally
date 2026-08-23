# Build (if needed) and run the FinAlly Docker container.
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$ImageName = "finally"
$ContainerName = "finally"
$Port = 8000

if (-not (Test-Path ".env")) {
    Write-Host "No .env file found. Copying .env.example -> .env"
    Copy-Item ".env.example" ".env"
    Write-Host "Edit .env and set OPENROUTER_API_KEY before using the AI chat."
}

New-Item -ItemType Directory -Force -Path "db" | Out-Null

$imageExists = docker images -q $ImageName
if ($Build -or [string]::IsNullOrWhiteSpace($imageExists)) {
    Write-Host "Building Docker image..."
    docker build -t $ImageName .
}

$existing = docker ps -aq -f "name=^$ContainerName$"
if (-not [string]::IsNullOrWhiteSpace($existing)) {
    Write-Host "Removing existing container..."
    docker rm -f $ContainerName | Out-Null
}

Write-Host "Starting container..."
docker run -d `
    --name $ContainerName `
    -p "${Port}:8000" `
    -v "${PWD}/db:/app/db" `
    --env-file .env `
    $ImageName

$Url = "http://localhost:$Port"
Write-Host "FinAlly is running at $Url"
Start-Process $Url
