@echo off
echo Creating Python 3.11 Virtual Environment...
py -3.11 -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo Failed to create venv!
    exit /b %ERRORLEVEL%
)

echo Upgrading pip and build tools...
call venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

echo Installing PyTorch with CUDA support...
call venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

echo Installing Python dependencies from requirements.txt...
call venv\Scripts\python.exe -m pip install -r requirements.txt

echo Done!
