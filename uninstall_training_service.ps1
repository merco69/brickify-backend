# Configuration du service
$serviceName = "BrickifyTrainingWorker"
$logPath = Join-Path $PSScriptRoot "logs"

# Vérifier si le service existe
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $service) {
    Write-Host "Le service $serviceName n'existe pas."
    exit 0
}

# Arrêter le service s'il est en cours d'exécution
if ($service.Status -eq "Running") {
    Write-Host "Arrêt du service..."
    Stop-Service -Name $serviceName -Force
    Start-Sleep -Seconds 2
}

# Supprimer le service
Write-Host "Suppression du service..."
$result = sc.exe delete $serviceName
if ($LASTEXITCODE -ne 0) {
    Write-Error "Erreur lors de la suppression du service: $result"
    exit 1
}

# Nettoyer les fichiers de logs
if (Test-Path $logPath) {
    Write-Host "Nettoyage des fichiers de logs..."
    Remove-Item -Path $logPath -Recurse -Force
}

Write-Host "Service désinstallé avec succès!" 