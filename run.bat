@echo off
setlocal

REM --- Configuration ---
set PYTHON_VERSION=3.13.5
set PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.13.5/python-3.13.5-amd64.exe
set PYTHON_INSTALLER_FILENAME=python-3.13.5-amd64.exe
set VENV_DIR=venv

REM =================================================================================
echo.
echo ======================== GUI Application Launcher =========================
echo.

REM --- Step 1: Check if Python is installed and available in PATH ---
echo Checking for Python...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not found on the system PATH.
    goto :install_python
) else (
    echo Python found.
    goto :setup_environment
)

:install_python
echo Attempting to download and install Python %PYTHON_VERSION%...
echo.
REM Use PowerShell (available on Windows 7 SP1 and later) to download the installer
powershell -Command "Write-Host 'Downloading Python installer...'; (New-Object System.Net.WebClient).DownloadFile('%PYTHON_INSTALLER_URL%', '%PYTHON_INSTALLER_FILENAME%')"

if not exist "%PYTHON_INSTALLER_FILENAME%" (
    echo.
    echo ERROR: Failed to download the Python installer.
    echo Please check your internet connection or download it manually from:
    echo %PYTHON_INSTALLER_URL%
    goto :end
)

echo.
echo Download complete. Starting Python installation...
echo This will happen in the background. Please be patient.
echo IMPORTANT: The installer will add Python to the system PATH.

REM Run the installer silently.
REM /quiet - silent installation
REM PrependPath=1 - This is the crucial step to add python to the PATH variable
start /wait %PYTHON_INSTALLER_FILENAME% /quiet PrependPath=1

REM Clean up the installer file
del %PYTHON_INSTALLER_FILENAME%

echo.
echo =================================================================================
echo Python has been installed. The system PATH has been updated.
echo.
echo IMPORTANT: You must close and re-run this script for the changes to take effect.
echo =================================================================================
goto :end

:setup_environment
REM --- Step 2: Manage virtual environment and dependencies ---
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    REM Create environment
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create the virtual environment.
        goto :end
    )

    REM Activate environment
    echo Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to activate the virtual environment.
        goto :end
    )

    REM Install dependencies
    echo Installing packages from requirements.txt...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install required packages. Please check requirements.txt.
        goto :end
    )
    echo Virtual environment created and dependencies installed.
) else (
    echo.
    echo Activating virtual environment...
    call "%VENV_DIR%\Scripts\activate.bat"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to activate the existing virtual environment.
        goto :end
    )
    echo Virtual environment activated.
)

REM --- Step 3: Run the Python script ---
echo.
echo =================================================================================
echo Starting the application...
echo =================================================================================
echo.
python main.py

REM Check the exit code of the python script
if %errorlevel% neq 0 (
    echo.
    echo The application closed unexpectedly with an error.
    echo Press any key to exit.
    pause >nul
)

REM Deactivate after the script finishes
call "%VENV_DIR%\Scripts\deactivate.bat"