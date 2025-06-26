<#
.SYNOPSIS
    Setup script for HomeLLMCoder project
.DESCRIPTION
    This script automates the setup of a Python virtual environment and installs all required dependencies.
    It works on both Windows and Unix-like systems.
#>

# Stop on first error
$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Message)
    Write-Host "`n=== $Message ===" -ForegroundColor Cyan
}

function Test-CommandExists {
    param([string]$Command)
    try {
        $null = Get-Command $Command -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Check Python version
Write-Header "Checking Python version"
$pythonVersion = (python --version 2>&1 | Select-String -Pattern "Python (\d+\.\d+\.\d+)").Matches.Groups[1].Value
if (-not $pythonVersion) {
    Write-Error "Python is not installed or not in PATH. Please install Python 3.9 or higher from https://www.python.org/downloads/"
    exit 1
}

Write-Host "Found Python $pythonVersion" -ForegroundColor Green

# Create virtual environment
Write-Header "Setting up virtual environment"
$venvPath = ".\venv"
$shouldCreateVenv = $true

if (Test-Path $venvPath) {
    Write-Host "Virtual environment already exists at $venvPath" -ForegroundColor Yellow
    $recreate = Read-Host "Do you want to recreate it? (y/N)"
    if ($recreate -eq 'y') {
        Remove-Item -Recurse -Force $venvPath
    } else {
        Write-Host "Using existing virtual environment" -ForegroundColor Green
        $shouldCreateVenv = $false
    }
}

if ($shouldCreateVenv) {
    Write-Host "Creating virtual environment at $venvPath"
    python -m venv $venvPath

    if (-not (Test-Path $venvPath)) {
        Write-Error "Failed to create virtual environment"
        exit 1
    }
}

# Activate the virtual environment
$activateScript = "$venvPath\Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "Failed to find activation script at $activateScript"
    exit 1
}

Write-Header "Activating virtual environment"
. $activateScript

# Upgrade pip
Write-Header "Upgrading pip"
python -m pip install --upgrade pip

# Install requirements
Write-Header "Installing Python dependencies"
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
} else {
    Write-Warning "requirements.txt not found. No Python dependencies to install."
}

# Install development dependencies if requirements-dev.txt exists
if (Test-Path "requirements-dev.txt") {
    Write-Header "Installing development dependencies"
    pip install -r requirements-dev.txt
}

# Install Node.js dependencies if package.json exists
if (Test-Path "package.json") {
    Write-Header "Installing Node.js dependencies"
    if (Test-CommandExists "npm") {
        npm install
    } else {
        Write-Warning "npm not found. Skipping Node.js dependencies."
    }
}

Write-Header "Setup complete!"
Write-Host "`nTo activate the virtual environment in the future, run:"
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host "`nTo deactivate, simply type 'deactivate'" -ForegroundColor Yellow
