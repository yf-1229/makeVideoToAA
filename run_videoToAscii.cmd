@echo off
REM Windows batch launcher for videoToAscii.py
REM 
REM This script provides an example of running videoToAscii.py on Windows.
REM It demonstrates:
REM   - Setting the GOOGLE_CREDS environment variable
REM   - Activating a Python virtual environment (optional, commented out)
REM   - Launching the Python script with forwarded arguments
REM   - Pausing at the end to display any errors

REM ========================================
REM Set environment variables (example)
REM ========================================
REM Uncomment and modify the line below to set your Google service account credentials path:
REM set GOOGLE_CREDS=C:\path\to\your\service-account-key.json

REM ========================================
REM Activate virtual environment (optional)
REM ========================================
REM Uncomment the appropriate line below if you are using a virtual environment:
REM For venv created in current directory:
REM call venv\Scripts\activate.bat
REM For venv created in specific path:
REM call C:\path\to\your\venv\Scripts\activate.bat

REM ========================================
REM Launch videoToAscii.py
REM ========================================
REM Forward all command-line arguments to the Python script
python videoToAscii.py %*

REM ========================================
REM Pause to display errors
REM ========================================
REM This ensures that if you double-click the batch file, the window stays open
REM so you can see any error messages.
pause
