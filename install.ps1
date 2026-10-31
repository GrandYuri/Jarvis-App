# Wymuszenie kodowania UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          JARVIS APP CONFIG              " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Pobranie klucza API od użytkownika
$rawKey = Read-Host "--Here you can paste your openai api key"
$apiKey = $rawKey.Trim()

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "[ERROR] Key can't be empty! Please open setup.exe again to enter your API key." -ForegroundColor Red
    Pause
    exit
}

if (-not $apiKey.StartsWith("sk-")) {
    Write-Host "[ERROR] Invalid API key format! The key must start with 'sk-'." -ForegroundColor Red
    Write-Host "Please open setup.exe again to enter your API key." -ForegroundColor Yellow
    Pause
    exit
}

# Zapisanie klucza w zmiennych środowiskowych użytkownika na stałe
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $apiKey, "User")
Write-Host "[OK] OpenAI Key is now saved!" -ForegroundColor Green

# Dynamiczne pobranie ścieżki folderu, w którym znajdują się pobrane pliki projektu
$ProjectPath = $PSScriptRoot
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Jarvis App.lnk"
$IconPath = Join-Path $ProjectPath "icon.ico"

# Tworzenie skrótu na Pulpicie wskazującego na pobrany katalog
$WscriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WscriptShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -Command ""& {Set-Location '$ProjectPath'; Start-Process python -ArgumentList 'jarvis.py' -WindowStyle Hidden}"""
$Shortcut.WorkingDirectory = $ProjectPath
$Shortcut.Description = "Jarvis App Dashboard"

if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}

$Shortcut.Save()
Write-Host "[OK] Shortcut 'Jarvis App' was created on Desktop!" -ForegroundColor Green
Write-Host ""
Write-Host "Everything ready! Powershell closes in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3