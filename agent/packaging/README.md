# Windows agentni paketlash (exe / MSI)

Bu fayllar **Windows'da** (haqiqiy mashina yoki Windows 11 VM — Parallels/UTM) ishlaydi.
macOS'da `.exe`/`.msi` kompilyatsiya qilib bo'lmaydi.

## 0. Tayyorgarlik (Windows'da bir marta)
- **Python 3.11+** o'rnating (python.org), "Add to PATH" belgilang.
- MSI uchun: **WiX** — `dotnet tool install --global wix` (avval .NET SDK kerak).
- Yoki oson yo'l: **Inno Setup** (https://jrsoftware.org/isdl.php).

## 1. config.json ni sozlang
`agent\config.example.json` ni oching va serveringizga moslang:
```json
{
  "server_url": "http://SIZNING_SERVER_IP:8001",
  "api_key": "dev-agent-key-change-me",
  "enabled_collectors": ["active_window","keyboard","usb","printer","software","clipboard","file_monitor","web","screenshot"]
}
```
> `server_url` — backend manzili (agent shu yerga ulanadi). `api_key` — serverdagi `AGENT_API_KEY` bilan bir xil bo'lsin.

## 2. Exe yasash
```bat
cd agent\packaging
build_exe.bat
```
Natija: `agent\dist\hp-dlp-agent.exe` (+ yonida `config.json`).
Shu exe'ni ikki marta bosib, darhol sinab ko'rsangiz bo'ladi — u serverga ma'lumot yubora boshlaydi.

## 3a. O'rnatuvchi — Inno Setup (tavsiya, oson)
`installer.iss` ni Inno Setup'da oching va **Compile** bosing (yoki `iscc installer.iss`).
Natija: `hp-dlp-agent-setup.exe`. Uni istalgan Windows'da ishga tushirib o'rnatasiz.
- `C:\Program Files\HP-DLP\` ga o'rnatadi
- `C:\ProgramData\HP-DLP\config.json` ni qo'yadi (keyin shuni tahrirlaysiz)
- Har logonда avtomatik ishga tushadi (HKLM Run)

## 3b. O'rnatuvchi — MSI (WiX)
```bat
cd agent\packaging
build_msi.bat
```
Natija: `agent\packaging\hp-dlp-agent.msi`. O'rnatish: `msiexec /i hp-dlp-agent.msi`.

## Qayerda nima
- Exe: `C:\Program Files\HP-DLP\hp-dlp-agent.exe`
- Sozlama: `C:\ProgramData\HP-DLP\config.json`
- agent_uid (barqaror ID): `C:\ProgramData\HP-DLP\.agent_uid`

## Avtomatik yangilanish (bir marta o'rnatib, keyin avtomatik)

Agent bir marta o'rnatilgach, yangi versiyalarni serverdan o'zi oladi:

1. `agent/core/version.py` da `VERSION` ni oshiring (masalan `0.5.0`).
2. `build_exe.bat` bilan yangi `hp-dlp-agent.exe` yasang.
3. Panelга kiring → **Agent yangilash** (superadmin) → versiya raqami + exe'ni yuklang.
4. O'rnatilgan agentlar 1 soat ichida (va har ishga tushganda) tekshiradi, yangiroq bo'lsa
   yuklab oladi, **SHA256** ni tekshiradi, o'zini almashtiradi va qayta ishga tushadi.

Shunday qilib bir marta MSI o'rnatasiz, keyingi yangilanishlar avtomatik.

## Eslatmalar
- Birinchi testda `--console` yoqilgan (loglarni ko'rasiz). Ishlab chiqarishда `build_exe.bat` dagi `--console` ni `--noconsole` ga almashtiring.
- Antivirus PyInstaller exe'sini shubhali deb belgilashi mumkin — ishlab chiqarishда **kod imzolash sertifikati** bilan imzolang.
- Haqiqiy "xizmat" (Windows Service) va himoya (tamper protection) — keyingi bosqich.
- Keylogger va ekran kuzatuvi — xodimlarning **yozma roziligi** bilan ishlating (huquqiy talab).
