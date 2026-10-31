# Jarvis App Dashboard

Welcome to **Jarvis App**! This lightweight background dashboard automates your workflow using OpenAI integration.

-----

## 📋 Requirements

* **Windows 10 / 11**
* **Python 3.x** (Ensure `Add Python to PATH` is checked during installation)
* (not required) An active **OpenAI API Key** (starts with `sk-`)

-----

## 🚀 Quick Installation

1. Download or clone this repository to your preferred location.
2. Run the `setup.bat` file by double-clicking it.
3. When prompted in the console, paste your **OpenAI API Key** and press `Enter`.
   * *If the key format is invalid or empty, you will be prompted to retry (`y`) or skip (`n`).*
4. Once configured, a shortcut named **Jarvis App** will automatically be created on your Desktop.

> **Note:** The installer sets up your API key permanently as a Windows User Environment Variable (`OPENAI_API_KEY`) and configures the desktop shortcut to launch the application silently in the background.

-----

## 📁 Structure

```text
Jarvis-App/
├── setup.bat             # Launcher
├── README.md             # Documentation
└── Scripts/
    ├── install.ps1       # PowerShell configuration script
    ├── jarvis.py         # Basically everything
    ├── jarvis_ai.py      # AI logic
    ├── icon.ico          # App icon
    └── *.json            # Config and data