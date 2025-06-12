@echo off
setlocal

:: Check admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run this script as Administrator.
    pause
    exit /b
)

echo ==========================
echo Installing Chocolatey...
echo ==========================

:: Install Chocolatey if not installed
where choco >nul 2>&1
if %errorLevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))"
) else (
    echo Chocolatey already installed.
)

echo ==========================
echo Installing required tools...
echo ==========================

:: Install aria2, megatools, wget, python3
choco install -y aria2 megatools wget python

:: Upgrade pip
python -m pip install --upgrade pip

:: Install python packages
echo ==========================
echo Installing python packages...
echo ==========================

pip install requests cloudscraper pyperclip tqdm termcolor beautifulsoup4

echo ==========================
echo All done!
echo You can now run Nanashi_Downloader.py
pause
