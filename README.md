# Senior Full-Stack Developer – Home Assignment

## Overview

This assignment simulates a simplified real-world system that displays a web-based interface of a chat between a Telegram bot and a remote participant.

The system should consist:
- A **React.js frontend** that displays a chat UI
- A **FastAPI (Python) backend** that manages a Telegram bot
- A single Telegram chat connection that acts as the remote participant

The focus of this assignment is on **architecture, clarity, and engineering judgment**, not visual polish or feature overload.

---

## Functional Requirements

### 1. Chat UI

The frontend must display a chat interface between the bot and the remote Telegram participant. 
It should include:

- A list of messages (incoming and outgoing)
- A text input for sending messages
- A send button (or Enter key support)

Each message must include:
- Message text
- Timestamp (time the message was sent)

The chat may not be consistent and may only present messages from the current session.

Incoming and outgoing messages should be visually distinguishable.

---

### 2. Telegram Bot Integration (Backend)

- The backend must manage a **Telegram bot instance**
- The bot must accept **only one active Telegram chat connection** (Should only accept interacting with one remote participant)
- Messages flow as follows:
  - Messages sent from the frontend are forwarded to the connected Telegram chat
  - Messages received by the Telegram bot are forwarded to the frontend as incoming messages

State management, concurrency handling, and message ordering should be handled safely.

---

### 3. Backend Configuration State

- Each Telegram bot is configured in a JSON file under `backend/app/config/bots/`.
- General app settings (Telegram mode, webhook URL, CORS, etc.) live in `.env` at the repo root.

---

## Communication Between Frontend and Backend

- The communication mechanism is up to you  
  (e.g. WebSockets, long polling, Server-Sent Events, etc.)
- The chosen approach should be justified by simplicity and correctness
- Real-time or near-real-time behavior is expected

---

## Technical Requirements

- **Frontend:** React.js
- **Backend:** FastAPI (Python)
- Code should be clean, readable, and maintainable
- Assumptions and trade-offs should be documented

---

## Prerequisites

- Node.js (18+ recommended)
- Python 3.10+
- Telegram account
- Telegram Bot Token (created via BotFather)

---

## Setup Instructions

### Environment files

Backend config lives at the **repo root** (not inside `backend/`). Copy the
templates and fill in your values:

```bash
cp .env.example .env
cp .env.development.example .env.development   # optional — local dev overrides
```

| File | Purpose |
|---|---|
| `.env` | Default / production config (`TELEGRAM_MODE=webhook`) |
| `.env.development` | Dev overrides, loaded when `ENVIRONMENT=development` (e.g. polling) |

Real shell environment variables override both files.

**Backend variables** (see `.env.example`):

| Variable | Description |
|---|---|
| `DEFAULT_MAX_ACTIVE_CHATS` | Default max conversations per bot when omitted from its JSON file |
| `TELEGRAM_MODE` | `webhook` \| `poll` |
| `TELEGRAM_API_BASE` | Telegram API base URL (default `https://api.telegram.org`) |
| `TELEGRAM_WEBHOOK_URL` | Public HTTPS base for webhook mode (e.g. ngrok URL) |
| `TELEGRAM_WEBHOOK_PATH` | Webhook route prefix (default `/telegram/webhook`; bot token is appended) |
| `TELEGRAM_WEBHOOK_SECRET` | Optional shared secret validated on inbound webhooks |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins (comma-separated) |

**Per-bot config** — copy the template and add one JSON file per bot:

```bash
cp backend/app/config/bots/example.json.example backend/app/config/bots/my_bot.json
# edit my_bot.json: set "token" and optional "max_active_chats"
```

**Frontend variables** (Vite — set inline or in `frontend/.env.local`):

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend base URL (default `http://localhost:8000`) |

---

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Run from `backend/` — the app loads `.env` from the repo root automatically.

| Mode | Command | When to use |
|---|---|---|
| **Webhook** (default) | `uvicorn app.main:app --reload` | Production or local dev with a public HTTPS tunnel (ngrok) |
| **Polling** | `ENVIRONMENT=development uvicorn app.main:app --reload` | Local dev — no public URL needed; uses `.env.development` |

Webhook mode registers each bot to:

```text
{TELEGRAM_WEBHOOK_URL}{TELEGRAM_WEBHOOK_PATH}/{bot_token}
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)

---

### Frontend

```bash
cd frontend
npm install
```

| Script | Command | When to use |
|---|---|---|
| **Dev** (real backend) | `npm run dev` | Default — talks to `http://localhost:8000` |
| **Custom backend URL** | `VITE_API_URL=http://localhost:8000 npm run dev` | Point at a different backend host/port |
| **Build** | `npm run build` | Production bundle |
| **Preview build** | `npm run preview` | Serve the production build locally |

App URL: [http://localhost:5173](http://localhost:5173)

---

### Typical local workflow

Use polling on the backend and the real frontend against it:

```bash
# Terminal 1 — backend (polling)
cd backend && source venv/bin/activate
ENVIRONMENT=development uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

---

### Docker Setup (Optional)

If `docker-compose.yml` is present, you can run the full stack in containers:

1. **Configure bots:**
   ```bash
   cp .env.example .env
   cp backend/app/config/bots/example.json.example backend/app/config/bots/bot.json
   # edit .env and backend/app/config/bots/bot.json
   ```

2. **Build and start the containers:**
   ```bash
   docker-compose up --build
   ```

| Service | URL | Notes |
|---|---|---|
| Frontend | http://localhost:5173 | Vite dev server (React) |
| Backend | http://localhost:8000 | FastAPI; health check at `/health` |

The frontend reads `VITE_API_URL` at build/dev time (defaults to `http://localhost:8000`).

To stop and remove the containers:

```bash
docker-compose down
```
