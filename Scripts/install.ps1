# Wymuszenie kodowania UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          JARVIS APP CONFIG              " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$keySaved = $false

# Pętla sprawdzania i wprowadzania klucza API
while ($true) {
    $rawKey = Read-Host "--Here you can paste your openai api key"
    $apiKey = $rawKey.Trim()

    if (-not [string]::IsNullOrWhiteSpace($apiKey) -and $apiKey.StartsWith("sk-")) {
        [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $apiKey, "User")
        Write-Host "[OK] OpenAI Key is now saved!" -ForegroundColor Green
        $keySaved = $true
        break
    } else {
        Write-Host "[ERROR] Invalid API key format! The key must start with 'sk-' and cannot be empty." -ForegroundColor Red
        
        $retryChoice = ""
        while ($retryChoice -ne "y" -and $retryChoice -ne "n") {
            $retryChoice = (Read-Host "Do you want to try entering the key again? (y/n)").Trim().ToLower()
        }

        if ($retryChoice -eq "n") {
            Write-Host "[INFO] Skipping API key setup. Continuing shortcut creation..." -ForegroundColor Yellow
            break
        }
        
        Write-Host ""
    }
}

# Ścieżki dynamiczne (skrypt jest w folderze Scripts)
$ScriptsPath = $PSScriptRoot
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Jarvis App.lnk"
$IconPath = Join-Path $ScriptsPath "icon.ico"

# Tworzenie skrótu na Pulpicie (wskazującym na folder Scripts jako roboczy)
$WscriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WscriptShell.CreateShortcut($ShortcutPath)

$Shortcut.TargetPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Arguments = "-WindowStyle Hidden -Command ""& {Set-Location '$ScriptsPath'; Start-Process python -ArgumentList 'jarvis.py' -WindowStyle Hidden}"""
$Shortcut.WorkingDirectory = $ScriptsPath
$Shortcut.Description = "Jarvis App Dashboard"

if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}

$Shortcut.Save()
Write-Host "[OK] Shortcut 'Jarvis App' was created on Desktop!" -ForegroundColor Green
Write-Host ""
Write-Host "Everything ready! Powershell closes in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3