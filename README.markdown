### Jarvis App Dashboard

Welcome to **Jarvis App**! This lightweight background dashboard automates your workflow using OpenAI integration. 

### 📋 Requirements

* **Windows 10 / 11**
* **Python 3.x** (Ensure Add Python to PATH is checked during installation)
* An active **OpenAI API Key** (starts with sk- – optional, but recommended for full AI features)

### 🚀 Quick Installation

1. Download or clone this repository to your preferred location.
2. Run the setup.bat file.
3. The installer will automatically configure everything: 

  * **API Key Check:** It checks if you already have an OpenAI key in your system. If not, it will prompt you to paste your **OpenAI API Key** (you can skip this by entering n).
  * **Virtual Environment:** It automatically creates a .venv folder and installs all required Python dependencies from requirements.txt.
  * **Desktop Shortcut:** A shortcut named **Jarvis App** will be created on your Desktop.

**Note:** The installer sets up your API key permanently as a Windows User Environment Variable (OPENAI_API_KEY) and configures the desktop shortcut to launch the application safely using the local virtual environment silently in the background. 

### 📁 Structure

text

Jarvis-App/
├── setup.bat             # Main launcher / installer
├── requirements.txt      # Automated Python packages list
├── README.md             # Documentation
└── Scripts/
    ├── install.ps1       # PowerShell configuration script
    ├── jarvis.py         # Main application dashboard
    ├── jarvis_ai.py      # AI logic integration
    ├── icon.ico          # App desktop icon
    ├── .gitignore        # Git ignore rules
    └── *.json            # Configuration and local data files

Use code with caution.