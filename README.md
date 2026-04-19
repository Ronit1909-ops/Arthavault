# UPI Finance Tracker – Backend API
> FastAPI · MongoDB Atlas · Redis Cloud · Google OAuth 2.0 · JWT

---

## Project Structure

```
Finance tracker/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + lifespan events
│   ├── config.py            # Pydantic Settings from .env
│   ├── database.py          # Motor async client + indexes
│   ├── models/
│   │   └── user.py          # User document, response, upsert schemas
│   ├── routers/
│   │   └── auth.py          # /auth/* endpoints (login, callback, me, logout)
│   ├── services/
│   │   └── auth_service.py  # DB-level auth logic (upsert user)
│   └── utils/
│       ├── jwt.py           # JWT create / decode helpers
│       └── redis.py         # aioredis client + session helpers
├── .env                     # Real secrets (git-ignored)
├── .env.example             # Template – commit this
├── .gitignore
├── docker-compose.yml       # Optional local Redis
├── requirements.txt
└── README.md
```

---

## 1 · Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| pip | latest |
| (optional) Docker Desktop | for local Redis |

---

## 2 · One-Time Setup

### 2a · Create & Activate Virtual Environment

```powershell
# In the project root
python -m venv .venv
.venv\Scripts\Activate.ps1          # PowerShell
# OR: .venv\Scripts\activate.bat   # CMD
```

### 2b · Install Dependencies

```powershell
pip install -r requirements.txt
```

### 2c · Configure Environment

The `.env` file is already pre-filled with your credentials.  
If you need to reset, copy from the template:

```powershell
copy .env.example .env
# Then edit .env with your actual values
```

---

## 3 · Google OAuth Console Setup

> **Do this once before the first run.**

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Open your OAuth 2.0 Client ID
3. Under **Authorised redirect URIs** add:
   ```
   http://localhost:8000/auth/callback
   ```
4. Under **Authorised JavaScript origins** add:
   ```
   http://localhost:8000
   ```
5. Save. Your `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are already in `.env`.

---

## 4 · MongoDB Atlas Setup

Your Atlas cluster is already configured. The `upi_tracker` database and
the `users` collection with indexes will be **created automatically** on first startup.

---

## 5 · Redis

**Option A – Redis Cloud** *(already configured in `.env`)*  
No action needed. The connection string is pre-set.

**Option B – Local Docker Redis** *(alternative for offline dev)*

```powershell
docker compose up -d redis
# Then change REDIS_URL in .env to:
# REDIS_URL="redis://localhost:6379"
```

---

## 6 · Run the Server

```powershell
# From the project root (with .venv active)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or via the Python entrypoint:

```powershell
python -m app.main
```

You should see:

```
INFO  Starting UPI Finance Tracker API …
INFO  MongoDB connected ✓  db=upi_tracker
INFO  Redis connected ✓
INFO  Uvicorn running on http://0.0.0.0:8000
```

---

## 7 · API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | ✗ | Health check |
| `GET` | `/docs` | ✗ | Swagger UI |
| `GET` | `/auth/login` | ✗ | Redirect to Google |
| `GET` | `/auth/callback` | ✗ | Google OAuth callback |
| `GET` | `/auth/me` | ✓ JWT | Current user profile |
| `POST` | `/auth/logout` | ✓ JWT | Invalidate session |

---

## 8 · Testing / Verification Commands

### Health check
```powershell
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0"}
```

### Open Swagger UI in browser
```
http://localhost:8000/docs
```

### Test Google OAuth (browser flow)
```
http://localhost:8000/auth/login
```
→ redirects to Google → you log in → redirects to `/auth/me` → shows your user JSON

### Test JWT manually (after login, copy the `access_token` cookie value)
```powershell
$token = "<paste-jwt-here>"
curl -H "Authorization: Bearer $token" http://localhost:8000/auth/me
```

### Verify MongoDB indexes
```powershell
# Using mongosh (Atlas connection)
mongosh "mongodb+srv://ronitpal2003:EANF1HdAzyGvxjfm@majistic.rqsmf.mongodb.net/upi_tracker"
> db.users.getIndexes()
```

### Verify Redis session
```powershell
# Using Redis CLI with cloud URL
redis-cli -u "redis://default:Ei6rlOp5KgFxZm1F1u1zYdzTaCgdOprt@redis-13558.c90.us-east-1-3.ec2.cloud.redislabs.com:13558"
> KEYS session:*
> GET session:<user-id>
```

---

## 9 · Auth Flow Diagram

```
Browser                    FastAPI                    Google
   |                          |                          |
   |--- GET /auth/login ----→ |                          |
   |                          |--- Redirect (302) -----→ |
   |                          |                          |
   |←-------------------- Google Consent Screen --------|
   |--- User clicks Allow --> |                          |
   |                          |←-- ?code=…&state=… -----|
   |                          |--- Token exchange ------→|
   |                          |←-- access_token ---------|
   |                          |--- GET /userinfo -------→|
   |                          |←-- {sub, email, name} ---|
   |                          |--- upsert DB             |
   |                          |--- create JWT            |
   |                          |--- store Redis session   |
   |←-- Set-Cookie: access_token=<jwt> (302 /auth/me) --|
   |--- GET /auth/me -------→ |                          |
   |←-- {id, email, name} ---|                          |
```

---

## 10 · Environment Variable Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `MONGO_URI` | ✓ | MongoDB Atlas SRV connection string |
| `MONGO_DB_NAME` | ✓ | Database name (`upi_tracker`) |
| `REDIS_URL` | ✓ | Redis connection URL |
| `GOOGLE_CLIENT_ID` | ✓ | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✓ | Google OAuth client secret |
| `GOOGLE_REDIRECT_URI` | ✓ | OAuth callback URL (must match Google Console) |
| `JWT_SECRET` | ✓ | Secret key for signing JWTs |
| `JWT_ALGORITHM` | – | Default: `HS256` |
| `JWT_EXPIRE_SECONDS` | – | Default: `86400` (24 h) |
| `APP_ENV` | – | `development` \| `production` |
| `CORS_ORIGINS` | – | Comma-separated allowed origins |
