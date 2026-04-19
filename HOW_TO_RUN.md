# How to Run — UPI Finance Tracker

## Prerequisites
- Python 3.10+ installed
- Node.js 18+ installed
- MongoDB Atlas URI (already in `.env`)
- Google OAuth credentials (already in `.env`)

---

## Step 1 — Open TWO terminal windows

Both must be opened at `d:\Projects\Finance tracker`.

---

## Terminal 1 — Backend (FastAPI)

```powershell
# Navigate to project root
cd "d:\Projects\Finance tracker"

# Activate virtual environment
.venv\Scripts\activate

# Start the backend server
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

✅ Backend is ready when you see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

API docs available at: http://localhost:8000/docs

---

## Terminal 2 — Frontend (React + Vite)

```powershell
# Navigate to frontend folder
cd "d:\Projects\Finance tracker\frontend"

# Install dependencies (first time only)
npm install

# Start the dev server
npm run dev
```

✅ Frontend is ready when you see:
```
  ➜  Local:   http://localhost:5173/
```

Open your browser at: **http://localhost:5173**

---

## Quick Summary

| What | Command | URL |
|---|---|---|
| Backend | `.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload` | http://localhost:8000 |
| Frontend | `npm run dev` (in `/frontend`) | http://localhost:5173 |
| API Docs | — | http://localhost:8000/docs |

---

## First-time setup (if `.venv` doesn't exist)

```powershell
# In project root
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

```powershell
# In frontend/
npm install
```
