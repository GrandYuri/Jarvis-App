# Wymuszenie kodowania UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          JARVIS APP CONFIG              " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. INTELIGENTNY FILTR: FOLDER VS ZIP ---
$ScriptsPath = $PSScriptRoot

# Jeśli w ścieżce występuje ".zip\" lub katalog Temp, oznacza to brak wyodrębnienia archiwum
if ($ScriptsPath -like "*.zip\*" -or $ScriptsPath -like "*\AppData\Local\Temp\*") {
    Write-Host "[ERROR] PRÓBA URUCHOMIENIA Z WNĘTRZA ARCHIWUM ZIP!" -ForegroundColor Red
    Write-Host "--------------------------------------------------" -ForegroundColor Red
    Write-Host "Aplikacja nie zainstaluje się wewnątrz spakowanego pliku." -ForegroundColor Yellow
    Write-Host "Musisz najpierw WYODRĘBNIĆ (rozpakować) pobraną paczkę na dysk." -ForegroundColor White
    Write-Host ""
    Write-Host "Naciśnij dowolny klawisz, aby zakończyć..." -ForegroundColor Yellow
    [void]$Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    Exit
}

# Pobieranie czystych, fizycznych ścieżek wyodrębnionego folderu projektu
$ProjectRoot = Split-Path $ScriptsPath -Parent
$VenvPath = Join-Path $ProjectRoot ".venv"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"
# ---------------------------------------------

$keySaved = $false

# 2. Sprawdzenie czy klucz już istnieje w profilu użytkownika Windows
$existingKey = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")

if (-not [string]::IsNullOrWhiteSpace($existingKey)) {
    Write-Host "[OK] Existing OpenAI API Key detected in your Windows profile!" -ForegroundColor Green
    $keySaved = $true
} else {
    # Pętla sprawdzania i wprowadzania klucza API (tylko gdy go brakuje)
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

# 3. SEKCJA AUTOMATYZACJI ŚRODOWISKA PYTHONA
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
    Write-Warning "[WARN] requirements.txt not found! Create it using 'pip freeze > requirements.txt'"
}

# 4. SEKCJA TWORZENIA SKRÓTU (Bez Start-Process, stabilne przekazywanie cudzysłowów)
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "          CREATING DESKTOP SHORTCUT      " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Jarvis App.lnk"
$IconPath = Join-Path $ScriptsPath "icon.ico"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"

$WscriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WscriptShell.CreateShortcut($ShortcutPath)

# Skrót wywołuje PowerShell w oknie ukrytym, wykonując sekwencję przejścia do katalogu i odpalenia Pythona
$Shortcut.TargetPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ""Set-Location '$ScriptsPath'; & '$VenvPython' jarvis.py"""
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