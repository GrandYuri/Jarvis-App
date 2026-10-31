# Pobierz ścieżkę do bieżącego folderu projektu
$ProjectPath = $PSScriptRoot
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Jarvis App.lnk"
$IconPath = Join-Path $ProjectPath "icon.ico"

Write-Host "Tworzenie skrótu dla Jarvis App..." -ForegroundColor Cyan

# Obiekt ComObject do tworzenia skrótu .lnk
$WscriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WscriptShell.CreateShortcut($ShortcutPath)

# Ścieżka do PowerShell, parametry (ukryte okno, zmiana katalogu i uruchomienie skryptu Pythona)
$Shortcut.TargetPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -Command ""& {Set-Location '$ProjectPath'; Start-Process python -ArgumentList 'jarvis.py' -WindowStyle Hidden}"""
$Shortcut.WorkingDirectory = $ProjectPath
$Shortcut.Description = "Jarvis App Dashboard"

# Przypisanie ikony, jeśli plik icon.ico istnieje w folderze
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
} else {
    Write-Host "Ostrzeżenie: Nie znaleziono pliku icon.ico w folderze projektu." -ForegroundColor Yellow
}

$Shortcut.Save()
Write-Host "Gotowe! Skrót 'Jarvis App' został pomyślnie utworzony na Pulpicie." -ForegroundColor Greengit add .