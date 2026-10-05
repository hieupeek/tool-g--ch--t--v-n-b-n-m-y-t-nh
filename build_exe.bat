@echo off
chcp 65001 > nul
echo ======================================================
echo    ĐANG ĐÓNG GÓI AUTOTYPER THÀNH FILE .EXE (WINDOWS)
echo ======================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [LOI] Khong tim thay Python tren may cua ban!
    echo Vui long cai dat Python tai https://www.python.org/ (nho tich vao "Add Python to PATH")
    pause
    exit /b
)

echo [1/3] Dang cai dat PyInstaller...
pip install pyinstaller -q

echo [2/3] Dang bien dich thanh file exe doc lap...
pyinstaller --noconsole --onefile --name "AutoTyper_Pro" auto_typer.py

if %errorlevel% equ 0 (
    echo.
    echo ======================================================
    echo [THANH CONG] File exe da duoc tao tai thu muc: dist\AutoTyper_Pro.exe
    echo Ban co the copy file nay sang bat ky may Windows nao de dung ngay!
    echo ======================================================
) else (
    echo.
    echo [THAT BAI] Co loi xay ra trong qua trinh dong goi!
)

pause
