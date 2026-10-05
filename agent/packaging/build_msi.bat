@echo off
REM HP DLP agent -> MSI (WiX v4). Avval build_exe.bat ishlatilган bo'lishi kerak.
REM WiX kerak:  dotnet tool install --global wix
REM Natija: agent\packaging\hp-dlp-agent.msi

cd /d %~dp0

where wix >nul 2>nul || (
  echo WiX topilmadi. O'rnating:  dotnet tool install --global wix
  exit /b 1
)

if not exist ..\dist\hp-dlp-agent.exe (
  echo ..\dist\hp-dlp-agent.exe yo'q. Avval build_exe.bat ni ishlating.
  exit /b 1
)
if not exist ..\dist\config.json copy ..\config.example.json ..\dist\config.json >nul

wix build product.wxs -o hp-dlp-agent.msi || exit /b 1
echo TAYYOR: %cd%\hp-dlp-agent.msi
