@echo off
echo ========================================
echo  Building PhoneFlash.exe
echo ========================================

cd /d E:\PhoneFlashPC

echo.
echo Installing dependencies...
pip install pyinstaller PySide6

echo.
echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building...
pyinstaller PhoneFlash.spec --noconfirm

echo.
echo ========================================
if exist "dist\PhoneFlash\PhoneFlash.exe" (
    echo  BUILD SUCCESSFUL!
    echo  Output: dist\PhoneFlash\PhoneFlash.exe
    echo ========================================
    echo.
    echo Contents of dist\PhoneFlash\:
    dir /b "dist\PhoneFlash\resources\adb\"
) else (
    echo  BUILD FAILED!
    echo ========================================
)

pause