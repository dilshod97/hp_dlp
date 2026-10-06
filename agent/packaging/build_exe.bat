@echo off
REM HP DLP agent -> bitta .exe (Windows'da ishga tushiring).
REM Natija: agent\dist\hp-dlp-agent.exe

cd /d %~dp0\..

echo [1/4] Virtual muhit...
python -m venv .venv || goto :err
call .venv\Scripts\activate || goto :err

echo [2/4] Kutubxonalar...
pip install --upgrade pip >nul
pip install -r requirements.txt -r requirements-windows.txt pyinstaller || goto :err

echo [3/4] Exe yasash (PyInstaller)...
pyinstaller --onefile --name hp-dlp-agent --noconsole ^
  --hidden-import win32timezone ^
  --collect-submodules pynput ^
  --collect-submodules watchdog ^
  --add-data "config.example.json;." ^
  main.py || goto :err

echo [4/4] config.json ni dist'ga nusxalash (MSI ichiga kiradi)...
if exist config.json (
  copy /Y config.json dist\config.json >nul
) else (
  copy /Y config.example.json dist\config.json >nul
  echo OGOHLANTIRISH: config.json topilmadi, namuna ishlatildi.
  echo config.example.json ni config.json ga nusxalab, server_url va api_key ni yozing, so'ng qayta build qiling.
)

echo.
echo TAYYOR: %cd%\dist\hp-dlp-agent.exe
echo Config exe bilan birga dist\config.json da — MSI uni avtomatik o'rnatadi (har kompyuterga qo'lda yozish shart emas).
goto :eof

:err
echo XATOLIK yuz berdi.
exit /b 1
