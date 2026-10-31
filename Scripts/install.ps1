# Wymuszenie kodowania UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          JARVIS APP CONFIG              " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. OKREŚLENIE ŚCIEŻEK - ZABEZPIECZENIE PRZED ZIPEM
# Pobieramy miejsce, skąd uruchomiono instalator (np. rozpakowany ZIP)
$SourceScriptsPath = $PSScriptRoot
$SourceProjectRoot = Split-Path $SourceScriptsPath -Parent

# Definiujemy STAŁĄ i bezpieczną ścieżkę instalacji w profilu użytkownika Windows
$InstallRoot = Join-Path $env:LOCALAPPDATA "JarvisDashboard"
$ScriptsPath = Join-Path $InstallRoot "Scripts"
$VenvPath = Join-Path $InstallRoot ".venv"
$RequirementsPath = Join-Path $InstallRoot "requirements.txt"

Write-Host "[INFO] Installing application to a secure location..." -ForegroundColor Yellow
Write-Host "Target path: $InstallRoot" -ForegroundColor Gray

# Kopiowanie plików do bezpiecznej lokalizacji (jeśli instalujemy z nowego miejsca)
if ($SourceProjectRoot -ne $InstallRoot) {
    if (-not (Test-Path $InstallRoot)) {
        New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
    }
    # Kopiujemy pliki źródłowe, omijając foldery wirtualne jeśli istniały
    Copy-Item -Path "$SourceProjectRoot\*" -Destination $InstallRoot -Recurforce -Exclude ".venv" -ErrorAction SilentlyContinue
    Write-Host "[OK] Files copied successfully to secure installation directory." -ForegroundColor Green
}

$keySaved = $false

# 2. Sprawdzenie czy klucz już istnieje w profilu użytkownika Windows
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

# 3. SEKCJA AUTOMATYZACJI ŚRODOWISKA PYTHONA (w bezpiecznej lokalizacji)
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "       PYTHON VIRTUAL ENVIRONMENT        " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

if (-not (Test-Path $VenvPath)) {
    Write-Host "[INFO] Creating virtual environment (.venv) in secure directory..." -ForegroundColor Yellow
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

# 4. SEKCJA TWORZENIA SKRÓTU (odnosi się WYŁĄCZNIE do bezpiecznego folderu)
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          CREATING DESKTOP SHORTCUT      " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Jarvis App.lnk"
$IconPath = Join-Path $ScriptsPath "icon.ico"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$JarvisScript = Join-Path $ScriptsPath "jarvis.py"

$WscriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WscriptShell.CreateShortcut($ShortcutPath)

# Skrót uruchamia Pythona i skrypt bezpośrednio z oficjalnego folderu instalacyjnego AppData
$Shortcut.TargetPath = $VenvPython
$Shortcut.Arguments = "`"$JarvisScript`""
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