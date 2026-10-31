<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jarvis App - Setup & Documentation</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #24292e;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            background-color: #f6f8fa;
        }
        .container {
            background: #ffffff;
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 32px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
        h1 {
            color: #0366d6;
            border-bottom: 2px solid #eaecef;
            padding-bottom: 10px;
            margin-top: 0;
        }
        h2 {
            color: #24292e;
            margin-top: 24px;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 6px;
        }
        code {
            background-color: #f0f3f6;
            padding: 3px 6px;
            border-radius: 4px;
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 85%;
        }
        pre {
            background-color: #f6f8fa;
            padding: 16px;
            border-radius: 6px;
            overflow: auto;
            border: 1px solid #e1e4e8;
        }
        .step-list {
            padding-left: 20px;
        }
        .step-list li {
            margin-bottom: 12px;
        }
        .note {
            background-color: #fffbe6;
            border-left: 4px solid #ffe58f;
            padding: 12px 16px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }
    </style>
</head>
<body>

<div class="container">
    <h1>Jarvis App Dashboard</h1>
    <p>Welcome to <strong>Jarvis App</strong>! This lightweight background dashboard automates your workflow using OpenAI integration.</p>

    <h2>📋 Requirements</h2>
    <ul>
        <li><strong>Windows 10 / 11</strong></li>
        <li><strong>Python 3.x</strong> (Ensure <code>Add Python to PATH</code> is checked during installation)</li>
        <li>An active <strong>OpenAI API Key</strong> (starts with <code>sk-</code>)</li>
    </ul>

    <h2>🚀 Quick Installation</h2>
    <ol class="step-list">
        <li>Download or clone this repository to your preferred location.</li>
        <li>Run the <code>setup.bat</code> file by double-clicking it.</li>
        <li>When prompted in the console, paste your <strong>OpenAI API Key</strong> and press <code>Enter</code>.
            <ul>
                <li><em>If the key format is invalid or empty, you will be prompted to retry (<code>y</code>) or skip (<code>n</code>).</em></li>
            </ul>
        </li>
        <li>Once configured, a shortcut named <strong>Jarvis App</strong> will automatically be created on your Desktop.</li>
    </ol>

    <div class="note">
        <strong>Note:</strong> The installer sets up your API key permanently as a Windows User Environment Variable (<code>OPENAI_API_KEY</code>) and configures the desktop shortcut to launch the application silently in the background.
    </div>

    <h2>🖥️ Usage</h2>
    <p>Double-click the <strong>Jarvis App</strong> shortcut on your Desktop to start the dashboard in background mode.</p>

    <h2>📁 Repository Structure</h2>
    <pre>
Jarvis-App/
├── setup.bat          # Main one-click launcher
├── jarvis.py          # Core application logic
├── icon.ico           # Application icon
├── README.markdown        # Documentation
└── Scripts/
    └── install.ps1    # PowerShell configuration script
    </pre>
</div>

</body>
</html>