# HP DLP

Korxona ma'lumotlari xavfsizligi (DLP) tizimi. Uch qismdan iborat:

| Papka | Nima | Texnologiya |
|-------|------|-------------|
| `backend/` | Markaziy server, API va ma'lumotlar bazasi | FastAPI + SQLModel |
| `agent/`   | Kompyuterlarga o'rnatiladigan kuzatuv dasturi | Python |
| `frontend/`| Admin boshqaruv paneli | React (Vite) |

## Arxitektura

```
   Agent (har bir kompyuterda)
        │  HTTPS + API kalit
        ▼
   Backend (FastAPI)  ──►  Ma'lumotlar bazasi (SQLite → PostgreSQL)
        │  Bearer token
        ▼
   Panel (React)  ──►  admin brauzerda ko'radi
```

**Muhim qoida:** agent ikki qatlamга bo'lingan —
- `agent/core/` — platformaga bog'liq emas (server bilan aloqa, navbat, sozlama). **Mac'da ham ishlaydi va sinaladi.**
- `agent/collectors/` — ma'lumot yig'uvchilar. Windows'ga xoslari Windows'da, Mac'da esa "mock" (soxta) yoki cross-platform versiyasi ishlaydi.

Shuning uchun ishning katta qismini Mac'da sinab bo'ladi. Windows'ga xos qismlar uchun Windows 11 virtual mashina (Parallels/UTM) kerak.

## Docker bilan ishga tushirish (eng oson)

Hammasi — baza, server, panel va demo agent — bitta buyruq bilan:

```bash
docker compose up --build
```

So'ng:
- **Panel:** http://localhost:5173  (token: `dev-dashboard-token-change-me`)
- **Server hujjati:** http://localhost:8001/docs

Xizmatlar: `db` (PostgreSQL), `backend` (FastAPI), `frontend` (React+nginx),
`agent` (Mac'da sinash uchun MOCK demo agent — panelда jonli ma'lumot ko'rsatadi).
Haqiqiy agentlar Windows kompyuterlarda ishlaydi, konteynerда emas.

To'xtatish: `docker compose down` (ma'lumotni ham o'chirish: `docker compose down -v`).

Sozlamalarni o'zgartirish (ixtiyoriy) — `.env` fayl yoki env orqali:
`AGENT_API_KEY`, `DASHBOARD_TOKEN`, `POSTGRES_PASSWORD`.

> Eslatma: backend host'da 8001-portда (8000 boshqa loyiha tomonidan band bo'lishi mumkin).

## Mac'da tez ishga tushirish (Docker'siz)

Uchidan-uchiga sinov (hammasi Mac'da):

```bash
# 1-terminal: server
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./run.sh                      # http://127.0.0.1:8000  (hujjat: /docs)

# 2-terminal: agent (Mac'da mock/cross-platform kolektorlar bilan)
cd agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
python main.py                # serverga ma'lumot yubora boshlaydi

# 3-terminal: panel
cd frontend
npm install
npm run dev                   # http://127.0.0.1:5173
```

## Windows'da agentni sinash

Windows 11 VM ichida:

```powershell
cd agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-windows.txt
copy config.example.json config.json
python main.py
```

Windows'da `collectors/factory.py` avtomatik ravishda haqiqiy Windows kolektorlarini tanlaydi.

## Holat

Bu loyiha hozir boshlang'ich bosqichda. Birinchi ishlaydigan qism: faol oyna + skrinshot kuzatuvi, server qabul qilishi, panelda ko'rsatishi. Qolgan modullar bosqichma-bosqich qo'shiladi (`docs/roadmap.md`).
