# Rivojlanish rejasi

## Bosqich 0 — Skelet (TAYYOR)
- [x] Backend (FastAPI) — hello, events, screenshot qabul qilish + panel API
- [x] Autentifikatsiya — agent kaliti va panel tokeni (sodda)
- [x] Agent yadrosi — sozlama, navbatli yuborish, qayta urinish
- [x] Kolektor arxitekturasi — Windows / mock ajratilgan
- [x] Faol oyna (Windows real + Mac mock) va skrinshot (cross-platform)
- [x] Panel (React) — KPI, agentlar, hodisalar, jonli yangilanish

## Bosqich 1 — Asosiy kuzatuv (TAYYOR)
- [x] Klaviatura (Windows pynput) — Backspace va modifikatorlar hisobga olingan; mock variant
- [x] Dastur faolligi va sarflangan vaqt (active_window + duration_sec)
- [x] USB disk ulanishi/uzilishi (barqaror poll bilan)
- [x] Printer hodisalari (qo'shilish/olib tashlanish). Job mazmuni — Bosqich 2'da
- [x] O'rnatilgan dasturlar ro'yxati (registr diff; mock variant)
- [x] Panelda o'zbekcha turlar, klaviatura matni, davomiylik ko'rsatiladi
- [x] Docker demo agentida hammasi jonli ko'rsatildi

## Panel yaxshilanishlari (TAYYOR)
- [x] Login/parol bilan kirish (foydalanuvchi jadvali, imzolangan token) — Bosqich 4 asosi
- [x] Agentni tahrirlash: ism-familiya (display_name), izoh, "ishdan bo'shagan" holati
- [x] Ushlangan fayllar: qabul qilish, ro'yxat va panelda ochib o'qish (matn/rasm)
- [x] Har bir ro'yxatda "Xodim" ustuni (kim ekani)
- [x] Qidiruv va filtrlar (agent, hodisa, fayl, yozishma)
- [x] "Dasturlar" bo'limi: qaysi dasturda qancha vaqt (xodim bo'yicha filtr)

## Bosqich 2 — DLP yadrosi (asosan TAYYOR)
- [x] Maxfiy ma'lumot aniqlash: kalit so'zlar + bank karta (Luhn) + pasport (regex)
- [x] Siyosat modeli: kalit so'zlar ro'yxati + detektorlar (panelдан tahrirlanadi)
- [x] Aniqlashlar yozishma va fayllarda ishlaydi, "Maxfiy ma'lumot" bo'limida chiqadi
- [x] Topilgan qiymatlar niqoblanadi (karta/pasport to'liq saqlanmaydi)
- [x] Ogohlantirish darajasi avtomatik "Yuqori" ga ko'tariladi
- [x] Barcha ro'yxatlarда sahifalash (pagination) — server + panel
- [ ] USB/fayl/clipboard orqali chiqishni haqiqiy bloklash (agent enforcement) — keyingi
- [ ] OCR (rasm ichidagi matnni o'qish) — keyingi

## Bosqich 3 — Kanallar (asosan TAYYOR)
- [x] Clipboard nazorati (Windows real + mock) — DLP tekshiruvidan o'tadi
- [x] Fayl monitoringi (Windows watchdog + mock): yaratish/o'zgartirish/o'chirish/ko'chirish
- [x] Veb-sayt nazorati (brauzer sarlavhasi asosida; to'liq URL — keyingi)
- [x] Panelда yangi bo'limlar: Veb-saytlar, Fayl harakatlari; Yozishmalar barcha kanalni ko'rsatadi
- [x] Barcha matnli kanallar (clipboard/telegram/email/klaviatura) DLP kalit so'z tekshiruvidan o'tadi
- [~] Telegram/E-mail — hozircha demo (haqiqiy ushlash keyingi bosqich, maxsus integratsiya kerak)
- [ ] Fayl-server nazorati (SMB audit)
- [ ] Veb to'liq URL (brauzer kengaytmasi/proksi)

## Bosqich 4 — Boshqaruv va xavfsizlik (asosan TAYYOR)
- [x] Login/parol + rollar: superadmin, admin, operator, auditor
- [x] Ruxsatlar (role enforcement): operator/auditor o'zgartira olmaydi (403)
- [x] Foydalanuvchilar boshqaruvi (yaratish, rol berish, o'chirish) — superadmin
- [x] Audit jurnali: login, siyosat, agent, foydalanuvchi, fayl ko'rish, tozalash
- [x] Ma'lumot saqlash muddati + tozalash (cleanup)
- [x] Rolga mos UI (menyu va tugmalar yashiriladi)
- [x] PostgreSQL (Docker)
- [x] Windows paketlash: PyInstaller exe + Inno Setup / WiX MSI (agent/packaging)
- [x] Avtomatik yangilanish: agent serverdan yangi exe olib o'zini yangilaydi (SHA256 bilan)
- [x] Panelда versiya yuklash (superadmin) + har agent versiyasi ko'rinadi
- [x] Ish vaqti: xodim qachondan qachongacha faol + jami faol vaqt (sana bo'yicha)
- [x] Sayt vaqti: qaysi saytда qancha o'tirgani (kun.uz uslubida)
- [x] Fayl manzili: ushlangan fayl kompyuterда qayerda edi (C:\...\Downloads)
- [x] Config bir marta yoziladi va MSI ichiga kiradi (har kompyuterga qo'lda yozilmaydi)
- [x] GitHub Actions: Windows'siz MSI build (yuklab olinadigan artifact)
- [ ] TLS/HTTPS (reverse-proxy bilan deploy)
- [ ] Har bir agentga alohida kalit + ro'yxatga olish tokeni
- [ ] Agent: Windows Service + tamper protection + imzolangan yangilanish
- [ ] Antivirus uchun kod imzolash sertifikati

## Bosqich 5 — Qo'shimcha
- [ ] Audio/video kuzatuv (huquqiy rozilik bilan)
- [ ] Ekran suv belgisi
- [ ] Hisobot eksporti (Excel/PDF)

## Eslatma: huquqiy tomon
Klaviatura, audio, video va ekran kuzatuvi xodimlarning yozma roziligini va
aniq ichki siyosatni talab qiladi. Ishga tushirishdan oldin HR/yurist bilan
kelishilsin.
