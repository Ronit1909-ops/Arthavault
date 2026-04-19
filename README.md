# 💰 ArthaVault — UPI Finance Tracker

> A full-stack personal finance tracker that automatically parses Indian bank statements (PDF), categorises transactions, visualises spending trends, and forecasts future expenses using ML.

---

## 🧠 What This Does

Most Indians manage their finances via UPI — but there's no single tool that gives you a clean picture of your spending across all banks. **ArthaVault** solves that.

You upload your bank's PDF statement → the app parses every transaction → you get:

- 📊 **Dashboard** with spending trends, category breakdown, and monthly comparisons
- 🔮 **ML Forecasting** to predict next month's spending based on your history
- 🔔 **Smart Notifications** when your spending spikes or patterns change
- 🔐 **Google OAuth login** — no passwords to remember
- 🏦 **Multi-bank support** — SBI, HDFC, ICICI, Kotak, IDBI, and more

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **FastAPI** | REST API framework (Python 3.11+) |
| **MongoDB Atlas** | Primary database (transactions, users) |
| **Motor** | Async MongoDB driver |
| **Redis Cloud** | Session storage & caching |
| **Google OAuth 2.0** | Authentication |
| **PyJWT** | Stateless JWT tokens |
| **pdfplumber + pikepdf** | PDF parsing & decryption |
| **Prophet (Facebook)** | ML spending forecasting |
| **Uvicorn** | ASGI server |

### Frontend
| Technology | Purpose |
|---|---|
| **React 18** | UI framework |
| **Vite** | Build tool & dev server |
| **Recharts** | Charts and data visualisation |
| **Zustand** | Global state management |
| **Axios** | HTTP client |

---

## 📁 Project Structure

```
ArthaVault/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Env-based config (Pydantic Settings)
│   ├── database.py          # MongoDB connection & indexes
│   ├── models/              # Pydantic data models
│   ├── routers/             # API route handlers
│   │   ├── auth.py          # Google OAuth + JWT endpoints
│   │   ├── statements.py    # PDF upload & parsing
│   │   ├── transactions.py  # Transaction CRUD
│   │   ├── dashboard.py     # Analytics & summary
│   │   └── forecasting.py   # ML forecast endpoints
│   ├── parsers/             # Bank-specific PDF parsers (SBI, HDFC, etc.)
│   ├── services/            # Business logic layer
│   └── utils/               # JWT, Redis, PDF decrypt helpers
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, Upload, Transactions, Login
│   │   ├── components/      # Reusable UI components
│   │   ├── services/        # API call functions
│   │   └── stores/          # Zustand state stores
│   └── package.json
├── .env                     # Secrets — never committed to git
├── .env.example             # Template — copy this to create .env
├── requirements.txt
└── docker-compose.yml       # Optional local Redis
```

---

## 🚀 How to Run (Local Development)

### Prerequisites

| Tool | Version |
|---|---|
| Python | 3.11+ |
| Node.js | 18+ |
| Git | any |

---

### Step 1 — Clone & Configure

```bash
git clone https://github.com/your-username/arthavault.git
cd arthavault
```

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your MongoDB URI, Google OAuth keys, etc.
```

> See `.env.example` for all required variables and where to get them.

---

### Step 2 — Backend Setup

Open a terminal in the project root:

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate          # PowerShell
# OR: .venv\Scripts\activate.bat  # CMD

# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

✅ Backend is ready when you see:
```
INFO:  MongoDB connected ✓
INFO:  Redis connected ✓
INFO:  Uvicorn running on http://0.0.0.0:8000
```

📖 **API docs (Swagger UI):** http://localhost:8000/docs

---

### Step 3 — Frontend Setup

Open a **second terminal** in the `frontend/` folder:

```powershell
cd frontend

# Install dependencies (first time only)
npm install

# Start the dev server
npm run dev
```

✅ Frontend is ready when you see:
```
➜  Local:   http://localhost:5173/
```

🌐 **Open your browser at:** http://localhost:5173

---

### Quick Reference

| Service | Command | URL |
|---|---|---|
| Backend API | `uvicorn app.main:app --port 8000 --reload` | http://localhost:8000 |
| Frontend | `npm run dev` (inside `/frontend`) | http://localhost:5173 |
| API Docs | — | http://localhost:8000/docs |

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in the values below:

| Variable | Required | Where to Get It |
|---|---|---|
| `MONGO_URI` | ✅ | [MongoDB Atlas](https://cloud.mongodb.com) → Connect → Drivers |
| `MONGO_DB_NAME` | ✅ | Set to `upi_tracker` |
| `REDIS_URL` | ✅ | [Redis Cloud](https://app.redislabs.com) → Database → Connect |
| `GOOGLE_CLIENT_ID` | ✅ | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `GOOGLE_CLIENT_SECRET` | ✅ | Same as above |
| `GOOGLE_REDIRECT_URI` | ✅ | Set to `http://localhost:8000/auth/callback` |
| `JWT_SECRET` | ✅ | Any long random string |
| `JWT_ALGORITHM` | – | Default: `HS256` |
| `JWT_EXPIRE_SECONDS` | – | Default: `86400` (24 hours) |
| `APP_ENV` | – | `development` or `production` |
| `CORS_ORIGINS` | – | Comma-separated allowed origins |

> **Google OAuth setup:** In [Google Cloud Console](https://console.cloud.google.com/apis/credentials), add `http://localhost:8000/auth/callback` as an Authorised Redirect URI.

---

## 📡 Key API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | ✗ | Health check |
| `GET` | `/docs` | ✗ | Swagger UI |
| `GET` | `/auth/login` | ✗ | Redirects to Google login |
| `GET` | `/auth/callback` | ✗ | Google OAuth callback |
| `GET` | `/auth/me` | ✅ JWT | Get current user |
| `POST` | `/auth/logout` | ✅ JWT | Invalidate session |
| `POST` | `/statements/upload` | ✅ JWT | Upload a PDF bank statement |
| `GET` | `/transactions` | ✅ JWT | List all transactions |
| `GET` | `/dashboard/summary` | ✅ JWT | Spending summary & trends |
| `GET` | `/forecasting/predict` | ✅ JWT | ML spending forecast |

---

## 🏦 Supported Banks

| Bank | Status |
|---|---|
| State Bank of India (SBI) | ✅ |
| HDFC Bank | ✅ |
| ICICI Bank | ✅ |
| Kotak Mahindra Bank | ✅ |
| IDBI Bank | ✅ |
| Bank of Baroda | ✅ |

Password-protected PDFs are supported — just enter your PDF password during upload (typically your date of birth in `DDMMYYYY` format).

---

## 📄 License

MIT — free to use, modify, and distribute.
