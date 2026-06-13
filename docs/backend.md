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
  config.py              Settings from env / .env (token, mode, webhook, max chats)
  models.py              Message + Sender/Status enums; SendMessageRequest
  connection_manager.py  WebSocket client registry + broadcast
  telegram_api.py        Thin HTTP wrapper over the Telegram Bot API
  telegram_service.py    Isolated Telegram gateway: send + parse updates
  telegram_poller.py     Pull driver: poll/mock loop → parse → domain
  main.py                FastAPI app: routes, wiring, lifespan
  chat/                  The chat domain
    chat_service.py        How incoming/outgoing messages are processed
    repository/            Data-access layer (DAL)
      chat_repository.py            ChatRepository — the storage interface
      in_memory_chat_repository.py  InMemoryChatRepository — in-memory impl
```

Dependency direction is one-way:

```
main → ChatService → { ChatRepository (DAL), ConnectionManager, TelegramService → TelegramAPI }
main → TelegramPoller → { TelegramService, ChatService }
```

`TelegramService` is a pure gateway with **no reference to the chat domain**: it
parses an update and returns an `IncomingMessage`. The `TelegramPoller` (poll
/ mock) and the webhook route are what pass that parsed message to
`ChatService` — coordination lives at the edges, not inside the gateway.

## Roles

- **`TelegramService` (gateway)** — pure Telegram I/O + parsing:
  `send(chat_id, text)`, `get_updates(offset)`, and `process_update(raw)` which
  parses a raw update into an `IncomingMessage` (or `None`) and **returns** it.
  No store, no clients, no domain handler, no background loop.
- **`TelegramPoller` (pull driver)** — owns the background pull loop (real
  `getUpdates` polling, or the mock feed standing in for it); fetches/synthesizes
  updates, parses via the gateway, and passes each `IncomingMessage` to
  `ChatService.handle_incoming`. (Webhook mode is push — the webhook route does
  this inline, no loop.)
- **`ChatService` (domain)** — the single place that decides processing:
  `send_message(...)`, `handle_incoming(IncomingMessage)`, `get_history(chat_id)`,
  `list_conversations()`, `reset()`. It coordinates the store, the connection
  manager, and the gateway.
- **`ChatRepository` (DAL)** — the storage interface the domain depends on.
  `InMemoryChatRepository` is the current implementation: messages
  **keyed per conversation (`chat_id`)** plus the active-chat set, all mutation
  behind an `asyncio.Lock`. A DB-backed repo implements the same interface — no
  domain changes.
- **`ConnectionManager`** — tracks connected agent clients, exposes
  `has_clients()`, and broadcasts events.
- **`TelegramAPI`** — pure HTTP: `sendMessage`, `getUpdates`, `set/deleteWebhook`.

## Message model & contract

The single message shape (matches the frontend exactly). `chat_id` is the
Telegram conversation it belongs to — a first-class field so the system extends
from one conversation to many without a reshape:

```
{ id, chat_id, text, timestamp, sender: "user"|"agent"|"bot", status }
```

Senders: **`user`** = the remote Telegram human (incoming); **`agent`** = the
back-office human, replying as the bot (outgoing — what we produce today);
**`bot`** = an automated server reply (reserved, not produced yet).

| Channel | Endpoint | Payload |
|---|---|---|
| List conversations | `GET /conversations` | → `[{ chat_id }]` |
| Load history | `GET /messages?chat_id=<id>` | → array of messages (ordered by timestamp) |
| Send | `POST /messages` | `{ id, chat_id, text, timestamp }` → the stored message (`409` if `chat_id` not active) |
| Server push | WebSocket `/ws` | `{type:"message", ...}` / `{type:"receipt", message_id, chat_id, status}` / `{type:"reset"}` |
| Telegram in | `POST /telegram/webhook` | raw Telegram update (webhook mode) |
| Admin reset | `POST /admin/reset` | clears all conversations (dev/admin) |

The server is the **authority** on `sender`/`status`: `POST /messages` only
trusts `id`/`chat_id`/`text`/`timestamp`; it forces `sender="agent"` and drives
the status lifecycle itself, so a client can never post as the user/bot or fake
delivery.

## Data flows

### Outgoing (agent → Telegram user) — `ChatService.send_message`

1. Reject with `NoActiveConversationError` (→ HTTP `409`) if `chat_id` isn't an
   active conversation — the bot can only reply within a chat the user started.
2. Store the message as `pending` with `sender="agent"`.
3. Ask the gateway to `send` to that `chat_id`.
4. Record the outcome (`sent` / `failed`) and broadcast a `receipt` so every
   connected client converges (the sending client also gets the HTTP response).

### Incoming (Telegram user → agent clients) — `ChatService.handle_incoming`

1. The `TelegramPoller` (poll/mock) **or** the webhook route gets a raw
   update, parses it via the gateway into an `IncomingMessage`, and passes it to
   `handle_incoming`.
2. **Reject if no agent is connected** (`ConnectionManager.has_clients()`) — the
   bot must not accept a conversation when no one is there.
3. Enforce single-active-chat (see below); drop if it's a different chat.
4. Store as `{sender:"user", status:"received"}` and broadcast `{type:"message"}`
   (carrying `chat_id`, so the client learns the conversation).

## Single-active-chat (a policy, not a limit)

A **conversation = one Telegram chat = one `chat_id`**. The limit is
**configurable** (`MAX_ACTIVE_CHATS`, default 1). `ChatRepository.register_chat`
admits a chat if it's already active or there's capacity; otherwise it returns
`False` and the message is dropped by `ChatService.handle_incoming`. The
capacity check and admission happen atomically inside the repository's lock, so
the limit can't be exceeded by a race. Outgoing sends are validated against the
active set (`is_active_chat`); a send to an unknown chat is rejected. Raising
`MAX_ACTIVE_CHATS` lets the back-office handle several users at once — storage
and routing are already keyed by `chat_id`.

## Telegram modes (`TELEGRAM_MODE`)

| Mode | Receive | Use |
|---|---|---|
| `webhook` (default) | `POST /telegram/webhook`, registered via `setWebhook` on boot | Production — needs a public HTTPS URL |
| `poll` | `getUpdates` long-poll loop; clears any stale webhook on boot | Local dev — no public URL needed (`.env.development`) |
| `mock` | `TelegramPoller` mock feed | Local testing with no live bot — outgoing sends are simulated, a fake user message arrives every 10s |

All receive paths converge on `gateway.process_update` → `chat.handle_incoming`,
so switching modes changes only how raw updates are obtained.

## Concurrency & resilience

- All shared-state mutation goes through `ChatStore`'s `asyncio.Lock`.
- The poll loop backs off on errors (e.g. a 409 Conflict when another instance
  is polling the same bot) instead of hammering the API.
- `httpx` request logging is filtered to redact the bot token, so the live
  getUpdates/sendMessage responses are visible in logs but the token never is.

## Configuration

Settings are layered: the shared `.env` (webhook / production defaults) plus
`.env.development` when `ENVIRONMENT=development` (polling overrides). Real
environment variables override both. All `.env*` are gitignored; `*.example`
templates are committed.

```
.env                 # production — TELEGRAM_MODE=webhook + webhook URL/secret
.env.development     # ENVIRONMENT=development — TELEGRAM_MODE=poll (overrides .env)
```

Variables:
- `TELEGRAM_BOT_TOKEN` — from BotFather (required for live use).
- `TELEGRAM_MODE` — `webhook` | `poll` | `mock`.
- `TELEGRAM_API_BASE` — Telegram Bot API base URL (default `https://api.telegram.org`).
- `TELEGRAM_WEBHOOK_URL` / `TELEGRAM_WEBHOOK_PATH` — webhook mode only.
- `MAX_ACTIVE_CHATS` — max simultaneous conversations (default `1`).

## Run

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload                              # default: webhook (.env)
ENVIRONMENT=development uvicorn app.main:app --reload      # polling (.env.development)
TELEGRAM_MODE=mock uvicorn app.main:app --reload           # no bot (overrides mode inline)
```

## Trade-offs & assumptions

- **In-memory persistence** — state resets on restart, which the brief allows
  (session-scoped). The store's async interface is the swap point for a DB.
- **Inline delivery** — `POST /messages` awaits Telegram and returns the final
  status. The planned queue/worker split (`integration.md`) would return
  `pending` immediately and rely on the WS receipt; the client already supports
  that, so the change is backend-only.
- **Conversation limit is config** — `MAX_ACTIVE_CHATS` (default 1) caps active
  conversations; the model is multi-ready (messages and routing are keyed by
  `chat_id`), so raising it needs no code change.
- **Agent must connect first** — incoming messages are rejected when no agent is
  connected, and dropped (not queued). "Deliver on next connect" would be a
  store-buffering change, not a policy change.
- **`/admin/reset` is unauthenticated** — it's a dev/test affordance; a real
  deployment would put auth in front of it (or omit it).
