# Configuration du service
$serviceName = "BrickifyTrainingWorker"
$displayName = "Brickify Training Worker"
$description = "Service d'entraînement continu pour Brickify"
$pythonPath = "python"
$scriptPath = Join-Path $PSScriptRoot "training_worker.py"
$logPath = Join-Path $PSScriptRoot "logs"
$workingDir = $PSScriptRoot

# Vérifier les prérequis
if (-not (Test-Path $pythonPath)) {
    Write-Error "Python n'est pas installé ou n'est pas dans le PATH"
    exit 1
}

if (-not (Test-Path $scriptPath)) {
    Write-Error "Le script training_worker.py n'existe pas à l'emplacement: $scriptPath"
    exit 1
}

# Créer le dossier de logs s'il n'existe pas
if (-not (Test-Path $logPath)) {
    New-Item -ItemType Directory -Path $logPath | Out-Null
    Write-Host "Dossier de logs créé: $logPath"
}

# Vérifier si le service existe déjà
$service = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($service) {
    Write-Host "Le service existe déjà. Arrêt et suppression..."
    Stop-Service -Name $serviceName -Force
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2
}

# Créer le chemin complet pour l'exécutable avec les paramètres
$binaryPath = "`"$pythonPath`" `"$scriptPath`""

# Créer le service avec les paramètres appropriés
Write-Host "Création du service..."
$result = sc.exe create $serviceName binPath= $binaryPath start= auto DisplayName= $displayName
if ($LASTEXITCODE -ne 0) {
    Write-Error "Erreur lors de la création du service: $result"
    exit 1
}

# Configurer les paramètres supplémentaires du service
sc.exe description $serviceName $description
sc.exe config $serviceName obj= "LocalSystem"
sc.exe config $serviceName start= auto
sc.exe config $serviceName type= own

# Configurer la récupération en cas d'échec
sc.exe failure $serviceName reset= 86400 actions= restart/60000/restart/60000/restart/60000

# Démarrer le service
Write-Host "Démarrage du service..."
Start-Service -Name $serviceName

# Vérifier que le service a démarré correctement
$service = Get-Service -Name $serviceName
if ($service.Status -ne "Running") {
    Write-Error "Le service n'a pas démarré correctement. Status: $($service.Status)"
    exit 1
}

Write-Host "Service installé et démarré avec succès!"
Write-Host "Nom du service: $serviceName"
Write-Host "Description: $description"
Write-Host "Chemin du script: $scriptPath"
Write-Host "Dossier de logs: $logPath" 