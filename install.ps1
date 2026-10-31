# Wymuszenie kodowania UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "       KONFIGURACJA JARVIS APP          " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Pobranie klucza API od użytkownika
$apiKey = Read-Host "--Here you can paste your openai api key"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "Klucz nie może być pusty! Konfiguracja przerwana." -ForegroundColor Red
    Pause
    exit
}

# Zapisanie klucza w zmiennych środowiskowych użytkownika na stałe
[Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $apiKey, "User")
Write-Host "[OK] Klucz OpenAI został pomyślnie zapisany w systemie!" -ForegroundColor Green

# Ścieżki dynamiczne (działają u każdego użytkownika)
$ProjectPath = $PSScriptRoot
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Jarvis App.lnk"
$IconPath = Join-Path $ProjectPath "icon.ico"

# Tworzenie skrótu na Pulpicie z ukrytym oknem konsoli
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
Write-Host "[OK] Skrót 'Jarvis App' został utworzony na Pulpicie!" -ForegroundColor Green
Write-Host ""
Write-Host "Wszystko gotowe! Okno zamknie się za 3 sekundy..." -ForegroundColor Yellow
Start-Sleep -Seconds 3