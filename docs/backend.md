# Backend — implementation overview

A FastAPI (Python) backend that manages a Telegram bot and bridges it to the
React client. This document describes what was built; see [`server.md`](./server.md)
for the original planning rationale and [`integration.md`](./integration.md) for
the cross-layer contract.

## Design goals

- **One-way dependencies / low coupling** — the Telegram gateway, the message
  store, and the WebSocket clients are mutually unaware. Exactly one component
  (`ChatService`) knows about all three and owns every processing decision.
- **Swappable implementations behind stable interfaces** — persistence is
  in-memory but sits behind an async store interface; the Telegram receive path
  is poll / webhook / mock behind one gateway. None of these leak into the
  domain logic.
- **Safe state, concurrency, and ordering** — a single lock guards shared state;
  messages are ordered by timestamp and never reordered downstream.

## Structure

```
backend/app/
  config.py              Settings from env / .env (token, mode, webhook config)
  models.py              Message + Sender/Status enums; SendMessageRequest
  store.py               In-memory message store + single-active-chat state (async-locked)
  connection_manager.py  WebSocket client registry + broadcast
  telegram_api.py        Thin HTTP wrapper over the Telegram Bot API
  telegram_service.py    Isolated Telegram gateway: send + receive/parse updates
  chat_service.py        The chat domain: how incoming/outgoing messages are processed
  main.py                FastAPI app: routes, wiring, lifespan
```

Dependency direction is one-way:

```
main → ChatService → { ChatStore, ConnectionManager, TelegramService → TelegramAPI }
```

`TelegramService` pushes parsed incoming messages **up** to `ChatService` via a
registered handler callback, so the gateway never learns what happens to them.

## Roles

- **`TelegramService` (gateway)** — talks to Telegram and nothing else:
  `send(chat_id, text)`, `process_update(raw)` (parse a raw update into a clean
  `IncomingMessage` and forward it to the handler), and the polling loop. It
  holds no store, no clients, and no single-chat policy.
- **`ChatService` (domain)** — the single place that decides processing:
  `send_user_message(...)`, `handle_incoming(IncomingMessage)`, `get_history()`.
  It coordinates the store, the connection manager, and the gateway.
- **`ChatStore`** — in-memory messages + the one bound `chat_id`, all mutation
  behind an `asyncio.Lock`. DB-ready async interface.
- **`ConnectionManager`** — tracks WebSocket clients and broadcasts events.
- **`TelegramAPI`** — pure HTTP: `sendMessage`, `getUpdates`, `set/deleteWebhook`.

## Message model & contract

The single message shape (matches the frontend exactly):

```
{ id, text, timestamp, sender: "user"|"bot", status }
```

| Channel | Endpoint | Payload |
|---|---|---|
| Load history | `GET /messages` | → array of messages (ordered by timestamp) |
| Send | `POST /messages` | full message object → the stored message |
| Server push | WebSocket `/ws` | `{type:"message", ...}` / `{type:"receipt", message_id, status}` |
| Telegram in | `POST /telegram/webhook` | raw Telegram update (webhook mode) |

The server is the **authority** on `sender`/`status`: `POST /messages` only
trusts `id`/`text`/`timestamp`; it forces `sender="user"` and drives the status
lifecycle itself, so a client can never post as the bot or fake delivery.

## Data flows

### Outgoing (user → Telegram) — `ChatService.send_user_message`

1. Store the message as `pending`.
2. Read the active `chat_id` from the store; ask the gateway to `send`.
3. Record the outcome (`sent` / `failed`) and broadcast a `receipt` so every
   connected client converges (the sending client also gets the HTTP response).

### Incoming (Telegram → clients) — `ChatService.handle_incoming`

1. The gateway (poller **or** webhook route) parses the update into an
   `IncomingMessage` and calls the handler.
2. Enforce single-active-chat (see below). Drop if it's a different chat.
3. Store as `{sender:"bot", status:"received"}` and broadcast `{type:"message"}`.

## Single-active-chat

The "one remote participant" requirement lives in `ChatStore.bind_chat`: the
first chat to message the bot is bound as the active one; messages from any
other chat return `False` and are dropped by `ChatService.handle_incoming`. The
check-and-set is inside the store's lock, so concurrent first-contacts can't
both bind (no race). Outgoing sends target this one bound chat; before anyone
has messaged the bot there is no `chat_id`, so a send fails cleanly.

## Telegram modes (`TELEGRAM_MODE`)

| Mode | Receive | Use |
|---|---|---|
| `poll` (default) | `getUpdates` long-poll loop; clears any stale webhook on boot | Local dev — no public URL needed |
| `webhook` | `POST /telegram/webhook`, registered via `setWebhook` on boot | Production — needs a public HTTPS URL |
| `mock` | none | Local testing with no live bot — outgoing sends are simulated as delivered |

Both real receive paths funnel into the same `process_update` → handler →
`ChatService`, so switching modes changes only how updates arrive.

## Concurrency & resilience

- All shared-state mutation goes through `ChatStore`'s `asyncio.Lock`.
- The poll loop backs off on errors (e.g. a 409 Conflict when another instance
  is polling the same bot) instead of hammering the API.
- `httpx` request logging is silenced so the bot token never lands in logs.

## Configuration

Environment variables (see `.env.example`; `.env` is gitignored):

- `TELEGRAM_BOT_TOKEN` — from BotFather (required for live integration).
- `TELEGRAM_MODE` — `poll` | `webhook` | `mock` (default `poll`).
- `TELEGRAM_WEBHOOK_URL` / `TELEGRAM_WEBHOOK_PATH` / `TELEGRAM_WEBHOOK_SECRET` —
  webhook mode only.

## Run

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

TELEGRAM_MODE=mock uvicorn app.main:app --reload   # local test, no bot
uvicorn app.main:app --reload                       # live, polling (reads ../.env)
```

## Trade-offs & assumptions

- **In-memory persistence** — state resets on restart, which the brief allows
  (session-scoped). The store's async interface is the swap point for a DB.
- **Inline delivery** — `POST /messages` awaits Telegram and returns the final
  status. The planned queue/worker split (`integration.md`) would return
  `pending` immediately and rely on the WS receipt; the client already supports
  that, so the change is backend-only.
- **Single conversation** — one bot ↔ one participant, matching the brief; no
  multi-conversation routing.
