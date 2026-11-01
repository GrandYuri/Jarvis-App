# Wymuszenie kodowania UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          JARVIS APP CONFIG              " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# --- DYNAMICZNE ŚCIEŻKI (Zawsze oparte o miejsce uruchomienia skryptu) ---
$ScriptsPath = $PSScriptRoot                      # To jest folder "Scripts", gdzie leży ten skrypt
$ProjectRoot = Split-Path $ScriptsPath -Parent    # To jest folder główny (np. "Jarvis-App-main")
$VenvPath = Join-Path $ProjectRoot ".venv"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"
$JarvisScript = Join-Path $ScriptsPath "jarvis.py"
# -------------------------------------------------------------------------

$keySaved = $false

# 1. Sprawdzenie czy klucz już istnieje w profilu użytkownika Windows
$existingKey = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")

if (-not [string]::IsNullOrWhiteSpace($existingKey)) {
    Write-Host "[OK] Existing OpenAI API Key detected in your Windows profile!" -ForegroundColor Green
    $keySaved = $true
} else {
    while ($true) {
        $rawKey = Read-Host "--Here you can paste your openai api key"
        $apiKey = $rawKey.Trim()

        if (-not [string]::IsNullOrWhiteSpace($apiKey) -and $apiKey.StartsWith("sk-")) {
            [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $apiKey, "User")
            $env:OPENAI_API_KEY = $apiKey
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
                Write-Host "[INFO] Skipping API key setup. Continuing environment setup..." -ForegroundColor Yellow
                break
            }
            Write-Host ""
        }
    }
}

# 2. SEKCJA AUTOMATYZACJI ŚRODOWISKA PYTHONA
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "       PYTHON VIRTUAL ENVIRONMENT        " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

if (-not (Test-Path $VenvPath)) {
    Write-Host "[INFO] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    Start-Process python -ArgumentList "-m venv `"$VenvPath`"" -Wait -NoNewWindow
    Write-Host "[OK] Virtual environment created!" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment (.venv) already exists." -ForegroundColor Green
}

# Instalacja zależności z requirements.txt
if (Test-Path $RequirementsPath) {
    Write-Host "[INFO] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    $PipPath = Join-Path $VenvPath "Scripts\pip.exe"
    Start-Process $PipPath -ArgumentList "install -r `"$RequirementsPath`"" -Wait -NoNewWindow
    Write-Host "[OK] All dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Warning "[WARN] requirements.txt not found!"
}

# 3. SEKCJA TWORZENIA SKRÓTU (Odporna na konflikt ZIP vs Folder)
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          CREATING DESKTOP SHORTCUT      " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Jarvis App.lnk"
$IconPath = Join-Path $ScriptsPath "icon.ico"

# 🔥 WYMUSZENIE ŚCIEŻKI ABSOLUTNEJ DO WYODRĘBNIONEGO FOLDERU (Bez .zip)
# Przekształcamy ścieżki na pełne ścieżki systemu plików (FileSystem), co odcina wirtualne ścieżki ZIP Windowsa
$FixedScriptsPath = (Get-Item $ScriptsPath).FullName
$FixedVenvPath = (Get-Item $VenvPath).FullName

$AbsoluteVenvPython = Join-Path $FixedVenvPath "Scripts\python.exe"
$AbsoluteJarvisScript = Join-Path $FixedScriptsPath "jarvis.py"

$WscriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WscriptShell.CreateShortcut($ShortcutPath)

# Skrót uruchamia PowerShell i przekazuje mu czyste, fizyczne ścieżki z dysku twardego
$Shortcut.TargetPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ""& {Set-Location '$FixedScriptsPath'; & '$AbsoluteVenvPython' '$AbsoluteJarvisScript'}"""
$Shortcut.WorkingDirectory = $FixedScriptsPath
$Shortcut.Description = "Jarvis App Dashboard"

if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath, 0"
}

$Shortcut.Save()
Write-Host "[OK] Shortcut 'Jarvis App' was created on Desktop!" -ForegroundColor Green
Write-Host ""
Write-Host "Everything ready! Powershell closes in 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3