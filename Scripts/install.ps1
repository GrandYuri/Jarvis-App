# --- SEKCJA AUTOMATYZACJI ŚRODOWISKA PYTHONA ---
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "       PYTHON VIRTUAL ENVIRONMENT        " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Przejście do głównego katalogu projektu (zakładamy, że skrypt jest w folderze Scripts, więc główny to folder wyżej)
$ProjectRoot = Split-Path $ScriptsPath -Parent
$VenvPath = Join-Path $ProjectRoot ".venv"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"

# 1. Tworzenie środowiska wirtualnego, jeśli nie istnieje
if (-not (Test-Path $VenvPath)) {
    Write-Host "[INFO] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    # Szukamy globalnego Pythona, aby utworzyć środowisko
    Start-Process python -ArgumentList "-m venv `"$VenvPath`"" -Wait -NoNewWindow
    Write-Host "[OK] Virtual environment created!" -ForegroundColor Green
} else {
    Write-Host "[OK] Virtual environment (.venv) already exists." -ForegroundColor Green
}

# 2. Instalacja zależności z requirements.txt
if (Test-Path $RequirementsPath) {
    Write-Host "[INFO] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
    $PipPath = Join-Path $VenvPath "Scripts\pip.exe"
    
    # Uruchomienie instalacji pakietów i czekanie na zakończenie procesu
    Start-Process $PipPath -ArgumentList "install -r `"$RequirementsPath`"" -Wait -NoNewWindow
    Write-Host "[OK] All dependencies installed successfully!" -ForegroundColor Green
} else {
    Write-Warning "[WARN] requirements.txt not found! Skipping package installation."
}
Write-Host ""