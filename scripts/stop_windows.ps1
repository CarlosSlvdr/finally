# Stop and remove the FinAlly container. Data in db/ is preserved.
$ErrorActionPreference = "Stop"

$ContainerName = "finally"

$existing = docker ps -aq -f "name=^$ContainerName$"
if (-not [string]::IsNullOrWhiteSpace($existing)) {
    Write-Host "Stopping FinAlly container..."
    docker rm -f $ContainerName | Out-Null
    Write-Host "Stopped."
} else {
    Write-Host "FinAlly container is not running."
}
