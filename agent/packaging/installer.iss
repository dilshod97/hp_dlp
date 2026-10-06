; HP DLP agent o'rnatuvchisi (Inno Setup).
; Inno Setup Compiler (iscc.exe) bilan kompilyatsiya qilinadi -> hp-dlp-agent-setup.exe
; Avval build_exe.bat ishlatib, dist\hp-dlp-agent.exe ni tayyorlang.
; Per-user o'rnatish: %LOCALAPPDATA%\HP-DLP (foydalanuvchi yoza oladi -> avtomatik yangilanish ishlaydi, admin shart emas).

#define AppName "HP DLP Agent"
#define AppVersion "0.6.2"
#define ExeName "hp-dlp-agent.exe"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\HP-DLP
DisableProgramGroupPage=yes
OutputBaseFilename=hp-dlp-agent-setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\dist\{#ExeName}"; DestDir: "{app}"; Flags: ignoreversion
; config.json faqat mavjud bo'lmasa ko'chiriladi (mavjudini ustiga yozmaydi)
Source: "..\dist\config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Registry]
; Har logonда avtomatik ishga tushadi (foydalanuvchi uchun)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "HP-DLP-Agent"; ValueData: """{app}\{#ExeName}"""; \
  Flags: uninsdeletevalue

[Run]
; O'rnatgandan so'ng darhol ishga tushirish
Filename: "{app}\{#ExeName}"; Description: "Agentni hozir ishga tushirish"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im {#ExeName}"; Flags: runhidden; RunOnceId: "StopAgent"
