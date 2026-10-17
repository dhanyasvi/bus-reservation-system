# 🚌 Bus Reservation System

> Book a bus seat by **just talking to it.**
> *"Book seat 5 from Bangalore to Chennai for Ravi"* → done. Seat reserved, fare calculated, payment recorded.

A FastAPI + MySQL reservation backend with a built-in **AI chat agent**, a clean web UI, and a classic REST API, all in one project. No API key? No problem: it ships with a **built-in resilient agent** that works with zero API credits.

---

## ✨ Features

| | |
|---|---|
| 💬 **Chat to book** | Natural-language booking, lookup, modification and cancellation |
| 🤖 **Single + multi-agent modes** | `/chat` for a single agent, `/chat/multi-agent` for a supervisor-routed team |
| 🛟 **Works offline from LLMs** | Leave `LLM_API_KEY` blank and the built-in agent takes over. A circuit breaker auto-falls back if your LLM provider fails |
| 🗺️ **Smart city matching** | Understands *Bengaluru, BLR, Madras, Bombay, Poona…* and maps them to real cities |
| 🎟️ **Full booking lifecycle** | Create, view, update, cancel, with seat uniqueness enforced by the database |
| 💳 **Payments & refunds** | Payment endpoint plus automatic 90% refund calculation on cancellation |
| 🔐 **Auth & admin controls** | User login, separate admin login, and an `X-Admin-Key`-protected admin API |
| 🛡️ **Abuse protection** | Sliding-window rate limiter per IP |
| 🧪 **Tested** | Pytest suite included |

**Cities:** Bangalore · Chennai · Hyderabad · Mumbai · Pune · Delhi · Kolkata · Mysore · Goa
**Bus layout:** 40 seats per bus · default fare ₹750

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.9+
- MySQL 8+ running locally

### 2. Set up the environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Create the database
```bash
mysql -u root -p < schema.sql
```
> 💡 **Windows:** if `mysql` isn't recognized, use the full path
> (`"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"`), or open `schema.sql` in **MySQL Workbench** and run it there.

### 4. Configure
```bash
cp .env.example .env            # Windows: copy .env.example .env
```
Open `.env` and set at least your MySQL password in `DB_URL`.

### 5. Run it
```bash
cd backend
uvicorn main:app --reload
```

### 6. Open it
| What | Where |
|---|---|
| 🖥️ Web UI | http://127.0.0.1:8000/ |
| 📖 Interactive API docs | http://127.0.0.1:8000/docs |

---

## 🎬 Try It in 60 Seconds

**1. Check the LLM connection** (optional)
```
GET /health/llm   →   {"status": "ok"}
```

**2. Book a seat by chatting**
```http
POST /chat
{ "message": "Book seat 5 from Bangalore to Chennai for Ravi" }
```

**3. Ask a follow-up**
```http
POST /chat
{ "message": "Which seats are still free from Bangalore to Chennai?" }
```

**4. Cancel and get your refund**
```http
POST /chat
{ "message": "Cancel Ravi's booking" }
```
The agent will ask you to **confirm before cancelling**. It never guesses missing details.

**5. Go admin**
```http
DELETE /admin/bookings
X-Admin-Key: <your ADMIN_API_KEY>
```
⚠️ This wipes all bookings. The chat agent is deliberately **not allowed** to do this.

---

## 🔌 API Overview

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/login` | User login |
| `POST` | `/auth/admin-login` | Admin login |
| `GET` | `/auth/me` | Current user |
| `POST` | `/bookings` | Create a booking |
| `GET` | `/bookings` | List bookings |
| `GET` | `/bookings/{id}` | Get one booking |
| `PUT` | `/bookings/{id}` | Update a booking |
| `DELETE` | `/bookings/{id}` | Cancel a booking |
| `POST` | `/bookings/{id}/payment` | Pay for a booking |
| `GET` | `/bookings/{id}/refund` | Refund details |
| `GET` | `/seats/available` | Free seats |
| `GET` | `/schedules` | Bus schedules |
| `GET` | `/schedules/{id}` | One schedule |
| `POST` | `/chat` | Chat with the booking agent |
| `POST` | `/chat/multi-agent` | Chat with the multi-agent team |
| `GET` | `/health/llm` | Check LLM connectivity |
| `GET/POST` | `/api/config` | View/update LLM settings (also from the UI) |
| `DELETE` | `/admin/bookings` | 🔒 Admin: delete all bookings |

Full request/response schemas live at `/docs`.

---

## ⚙️ Configuration (`.env`)

| Variable | Description | Default |
|---|---|---|
| `LLM_API_KEY` | OpenAI / Groq / Gemini key. **Leave blank to use the built-in agent** | *(blank)* |
| `LLM_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name | `gpt-4o-mini` |
| `ADMIN_API_KEY` | Secret for admin endpoints | *(set your own!)* |
| `DB_URL` | SQLAlchemy connection string | `mysql+pymysql://root:password@localhost/busdb` |

> 🔑 **Special characters in your DB password?** URL-encode them (`@` → `%40`, `#` → `%23`).

---

## 🗂️ Project Structure

```
bus-reservation/
├── schema.sql              # Database tables (bookings, schedules)
├── requirements.txt
├── .env.example            # Copy to .env
└── backend/
    ├── main.py             # FastAPI app & routes
    ├── services.py         # Booking business logic
    ├── models.py           # Database models
    ├── schemas.py          # Request/response schemas
    ├── database.py         # DB connection
    ├── single_agent.py     # Single chat agent + circuit breaker
    ├── multi_agent.py      # Supervisor-routed multi-agent
    ├── tools.py            # Tools the agents can call
    ├── llm_client.py       # LLM provider client
    ├── auth.py             # Authentication
    ├── rate_limiter.py     # Per-IP rate limiting
    ├── config.py           # Settings loader
    ├── test_app.py         # Tests
    └── static/             # Web UI (HTML, CSS, JS)
```

---

## 🧪 Run the Tests
```bash
cd backend
pytest
```

---

## 🩺 Troubleshooting

| Problem | Fix |
|---|---|
| `'mysql' is not recognized` (Windows) | Use the full path to `mysql.exe`, add MySQL's `bin` folder to PATH, or use MySQL Workbench |
| Database connection error on startup | Check the password in `DB_URL` and that the MySQL service is running |
| `/health/llm` fails | Your key may be wrong or expired. Clear `LLM_API_KEY` to use the built-in agent |
| `429 Too Many Requests` | You hit the rate limiter. Wait a minute |

---

## 🔒 Security Notes
- **Never commit `.env`.** It's already in `.gitignore`.
- Change `ADMIN_API_KEY` from any default before sharing or deploying.
- If an API key was ever exposed, rotate it.

---

## 🛣️ Ideas for Next Steps
- Real payment gateway integration
- Seat-map picker in the web UI
- Email/SMS ticket confirmations
- Docker Compose for one-command setup

Happy travels! 🚍
