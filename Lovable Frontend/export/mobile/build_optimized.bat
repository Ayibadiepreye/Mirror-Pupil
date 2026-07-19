@echo off
REM Build optimized APKs for lower-end devices
echo ========================================
echo Mirror Pupil - Optimized Build Script
echo ========================================
echo.

echo [1/4] Cleaning previous builds...
call flutter clean
if errorlevel 1 goto error

echo.
echo [2/4] Getting dependencies...
call flutter pub get
if errorlevel 1 goto error

echo.
echo [3/4] Building split APKs (optimized for size)...
call flutter build apk --release --split-per-abi
if errorlevel 1 goto error

echo.
echo [4/4] Build complete!
echo.
echo ========================================
echo APKs created in build\app\outputs\flutter-apk\
echo.
echo For friend's lower-end phone, use:
echo   app-armeabi-v7a-release.apk  (15MB - 32-bit ARM)
echo   OR
echo   app-arm64-v8a-release.apk    (18MB - 64-bit ARM)
echo.
echo If unsure, use:
echo   app-release.apk              (45MB - works on all devices)
echo ========================================
pause
exit /b 0

:error
echo.
echo ========================================
echo ERROR: Build failed!
echo ========================================
pause
exit /b 1
