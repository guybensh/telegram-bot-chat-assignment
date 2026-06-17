# Backend — implementation overview

A FastAPI (Python) backend that manages a Telegram bot and bridges it to the
React client. This document describes what was built; see [`integration.md`](./integration.md) for
the cross-layer contract.

## Design goals

The server follows a **handler → service → repository** layout:

- **Handlers** (`routes/`, listeners) — parse HTTP/WebSocket/Telegram input, map
  errors to responses, and delegate. No business rules.
- **Services** (`domain/bot`, `domain/chat`) — own processing decisions: admit
  conversations, send/receive messages, enforce capacity.
- **Repositories & providers** — hide storage and external messaging behind
  interfaces (`ChatRepository`, `BotRepository`, `MessageProvider`).

Dependencies point **inward** only: handlers call services; services call
repositories and providers. Nothing in persistence or Telegram I/O imports route
or domain orchestration code.

- **Low coupling at the edges** — because responsibilities are separated,
  listeners (poll / webhook), the message provider, WebSocket broadcast,
  and repositories do not call one another. `ChatService` coordinates them and
  is the single place that decides what happens to each message.
- **Single responsibility** — each module is scoped to one job. Splitting the stack this way keeps changes localized.
- **Swappable implementations behind stable interfaces** — persistence is
  in-memory today but sits behind async repository interfaces; Telegram I/O sits
  behind `MessageProvider`, with receive mode chosen at startup (poll / webhook).
- **Production first** — with polling, the server keeps a long-lived
  `getUpdates` connection to Telegram for every bot; with webhooks, Telegram
  pushes each update as a short inbound HTTP request and the server does not
  hold that outbound connection. Polling remains available for local dev when a
  public HTTPS URL isn't practical; both paths feed the same `ChatService` (see
  [Telegram modes](#telegram-modes-telegram_mode)).
- **Safe state, concurrency, and ordering** — shared repository state is guarded
  by locks; messages are ordered by timestamp and never reordered downstream.

## Structure

```
backend/app/
  main.py                  FastAPI app, lifespan, CORS, router + listener wiring
  bootstrap.py             AppContext, build_app_context, load_bots_from_config
  models.py                Shared API DTOs (Message, ChatSummary, …)
  connection_manager.py    WebSocket client registry + broadcast
  logging_setup.py         Token redaction in httpx logs
  config/
    settings.py            Settings from .env
    bots.py                Loads bot credentials from bots.json
    bots.json              Per-bot token + max_active_chats (gitignored; see .example)
    bots.json.example
  domain/
    bot/
      bot_service.py       Bot registry
      record.py            BotRecord, BotInboxItem
      repository/          BotRepository + InMemoryBotRepository
    chat/
      chat_service.py      Message processing (scoped per bot)
      repository/          ChatRepository + InMemoryChatRepository
  listeners/
    factory.py             create_listeners() — picks mode from TELEGRAM_MODE
    protocol.py            MessageListener interface
    polling_listener.py    Poll mode — starts TelegramPoller per bot
    webhook_listener.py    Webhook mode — registers setWebhook on boot
  messaging_providers/
    protocol.py            MessageProvider ABC
    types.py               IncomingMessage
    telegram/
      client.py            Stateless Telegram HTTP client
      provider.py          TelegramProvider (MessageProvider implementation)
      poller.py            getUpdates long-poll loop (used by PollingListener)
      utils.py             Webhook URL helpers
  middleware/
    cors.py                CORS registration
    telegram_auth.py       Webhook secret validation
  routes/
    api.py                 App-facing REST + WebSocket
    webhook.py             POST /telegram/webhook/{bot_id}
```

## Handler / API layer

The HTTP surface is a thin adapter: route handlers validate input, map domain
exceptions to HTTP status codes, and delegate to `BotService` / `ChatService`.
They should not contain business rules — those live in the domain.

**Current layout (kept intentionally small):**

| Module | Responsibility |
|---|---|
| `routes/api.py` | App-facing REST + WebSocket |
| `routes/webhook.py` | separate router with its own auth middleware |

### Future scaling — split by domain

When the route layer grows (auth, admin endpoints, metrics, API versioning), split **`routes/api.py`** into domain-aligned routers:

```
routes/
  bot_routes.py       GET /bots  → BotService (+ inbox enrichment)
  chat_routes.py      prefix /bots/{username} → chat-summaries + messages, POST /reset
  infra_routes.py     GET /health, WS /ws  (app wiring, not bot/chat domain)
  __init__.py         compose via app_router(deps) + webhook_router(deps)
  webhook.py          (unchanged — Telegram ingress, not agent API)
```

Each domain router delegates only to its matching service (`BotService`,
`ChatService`). Handlers stay thin: validate input, map exceptions to HTTP,
call the domain.


### API & WebSocket contract

| Channel | Endpoint | Payload |
|---|---|---|
| List bots | `GET /bots` | → `[BotInboxItem]` |
| List chat summaries | `GET /bots/{username}/chat-summaries` | → `[ChatSummary]` |
| Load history | `GET /bots/{username}/chats/{chat_id}/messages` | → `[Message]` (includes `read_at`) |
| Send | `POST /bots/{username}/chats/{chat_id}/messages` | `SendMessageRequest` → `Message` |
| Mark read | `POST /bots/{username}/chats/{chat_id}/messages/read` | `{ read_at }` → `{ chat_id, read_at, marked_count }` |
| Server push | WebSocket `/ws` | `{type:"message", bot_username, …Message fields}` / `{type:"receipt", message_id, chat_id, bot_username, status}` / `{type:"reset"}` |
| Telegram in | `POST /telegram/webhook/{bot_id}` | raw Telegram update (webhook mode) |
| Reset | `POST /reset` | clears all conversations (dev) |


## Roles

- **`MessageProvider` (protocol)** — outbound delivery, incoming parsing, and
  provider-side credentials. `TelegramProvider` is the current implementation.
- **`TelegramClient`** — stateless Telegram Bot HTTP client (`getMe`,
  `sendMessage`, `getUpdates`, `setWebhook`, `deleteWebhook`).
- **`MessageListener` (protocol)** — startup hook for the receive path.
  `PollingListener` and `WebhookListener` are selected by
  `TELEGRAM_MODE` via `create_listeners()`.
- **`TelegramPoller`** — background `getUpdates` long-poll loop;
  used by `PollingListener`.
- **`BotService` (domain)** — bot registry: register bots from config, resolve
  by id or username.
- **`ChatService` (domain)** — the single place that decides message processing:
  `send_message(...)`, `handle_incoming_message(...)`, `list_messages(...)`,
  `list_chat_summaries(...)`, `reset()`. Coordinates the repository,
  connection manager, and message provider.
- **`ChatRepository` / `BotRepository`** — storage interfaces the domain
  depends on. Easy replacable storage type — no domain changes.
- **`ConnectionManager`** — tracks connected agent clients, exposes
  `has_clients()` (gates live WebSocket push), and broadcasts events.

## Message model & contract

Defined in `models.py`. The same `Message` shape is used all around the system — the frontend can treat
them interchangeably.
 
### `Message`

```json
{
  "id": "uuid-or-tg-123",
  "bot_id": "123456789",
  "chat_id": "987654321",
  "text": "Hello",
  "timestamp": "2026-06-12T09:30:00.000Z",
  "sender": "user",
  "status": "received",
  "read_at": null
}
```

| Field | Type | Meaning |
|---|---|---|
| `id` | `str` | Stable message identity. |
| `bot_id` | `str` | Which bot this message belongs to. |
| `chat_id` | `str` | Provider conversation identifier. |
| `text` | `str` | Message body. |
| `timestamp` | ISO 8601 `datetime` | When the message was sent. Used for ordering. |
| `sender` | `Sender` | Who produced the message (see below). |
| `status` | `Status` | Delivery state (see below). |
| `read_at` | ISO 8601 `datetime` or `null` | When the agent marked the message read in the inbox. `null` = unread (see below). |

### `sender` — who sent it

| Value | Direction | Meaning |
|---|---|---|
| `user` | Incoming | The remote Telegram participant (a real human). |
| `agent` | Outgoing | The back-office human replying **as the bot** — what the system produces today. |
| `bot` | Outgoing (reserved) | A future automated server reply. Not produced yet; kept distinct from `agent`. |

### `status` — delivery lifecycle

`status` describes **transport/delivery**, not inbox read state (that is `read_at`).

| Value | Used on | Meaning |
|---|---|---|
| `pending` | Outgoing (`agent`) | Stored locally; Telegram delivery in progress. |
| `sent` | Outgoing (`agent`) | Delivered to Telegram successfully. |
| `failed` | Outgoing (`agent`) | Telegram delivery failed. |
| `received` | Incoming (`user`) | Constant for stored incoming messages. |

Outgoing flow: `pending` → `sent` | `failed`. The HTTP response carries the
final status; a WebSocket `{type:"receipt"}` is also broadcast so other
connected clients converge.

### `read_at` — agent read state

Orthogonal to `status`. Tracks whether the **back-office agent** has seen an
incoming user message in the inbox.

| Value | Meaning |
|---|---|
| `null` | Unread — typically incoming `user` messages not yet seen by the agent. |
| ISO 8601 `datetime` | Read — set when the agent opens the thread (or when a live message arrives while that thread is open). |

- Incoming user messages are stored with `read_at: null`.
- Outgoing `agent` / `bot` messages usually keep `read_at: null` (not used for badges).
- Mark-read: `POST /bots/{username}/chats/{chat_id}/messages/read` with body
  `{ "read_at": "<timestamp>" }` — sets `read_at` on all unread user messages in
  that thread with `timestamp <= read_at`. Returns `{ chat_id, read_at, marked_count }`.
- Unread rule: `sender == "user" && read_at == null` (see
  [Unread badges: prefetch vs server `unread_count`](#unread-badges-prefetch-vs-server-unread_count)).

## Data flows

### Outgoing (agent → Telegram user) — `ChatService.send_message`

1. Reject with `NoActiveConversationError` (→ HTTP `409`) if `chat_id` isn't an
   active conversation — the bot can only reply within a chat the user started.
2. Store the message as `pending` with `sender="agent"`.
3. Ask `MessageProvider.send_message` to deliver to that `chat_id`.
4. Record the outcome (`sent` / `failed`) and broadcast a `receipt` so every
   connected client converges (the sending client also gets the HTTP response).

### Incoming (Telegram user → agent clients) — `ChatService.handle_incoming_message`

1. A listener (`PollingListener`) **or** the webhook route
   obtains a raw update, parses it via `MessageProvider.parse_incoming_message`,
   and passes the `IncomingMessage` to `handle_incoming_message`.
2. Resolve the bot; ignore unknown `bot_id`.
3. Enforce per-bot active-chat capacity (see below); drop if over limit.
4. Store as `{sender:"user", status:"received", read_at: null}` in the repository.
5. **Broadcast only if an agent is connected** (`ConnectionManager.has_clients()`)
   — push `{type:"message"}` (with `bot_username` and message fields). If no
   client is connected, the message remains stored; the agent loads it later via
   `GET /bots/{username}/chat-summaries` and
   `GET /bots/{username}/chats/{chat_id}/messages`.

## Single-active-chat (a policy, not a limit)

A **conversation = one Telegram chat = one `chat_id`**. The limit is
**configurable** (`MAX_ACTIVE_CHATS`, default 1). `ChatRepository.register_chat`
admits a chat if it's already active or there's capacity; otherwise it returns
`False` and the message is dropped by `ChatService.handle_incoming_message`. The
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

**Production first**

- **Connections** — polling keeps one long-lived outbound connection per bot;
  webhooks accept short inbound requests only when an update arrives.
- **Push vs pull** — webhooks deliver updates as Telegram receives them; polling
  repeatedly asks Telegram for new updates on that open connection.
- **Poll when developing locally** — `getUpdates` works without registering a
  public URL (no ngrok). Switch via `TELEGRAM_MODE=poll` in `.env.development`.

All receive paths converge on `MessageProvider.parse_incoming_message` →
`ChatService.handle_incoming_message`, so switching modes changes only how raw
updates are obtained and registered at startup.

## Concurrency & resilience

- All shared-state mutation goes through repository `asyncio.Lock`s.
- The poll loop backs off on errors (e.g. a 409 Conflict when another instance
  is polling the same bot) instead of hammering the API.
- `httpx` request logging is filtered to redact the bot token, so the live
  getUpdates/sendMessage responses are visible in logs but the token never is.

## Configuration

Settings are layered: `.env` at the repo root plus `.env.development` when
`ENVIRONMENT=development`. Bot tokens live in `backend/app/config/bots.json`
(a single file with a `bots` array). Real environment variables override
`.env` files.

```
.env                              # TELEGRAM_MODE, webhook URL, CORS, …
.env.development                  # ENVIRONMENT=development — polling overrides
backend/app/config/bots.json      # per-bot token + max_active_chats (gitignored)
backend/app/config/bots.json.example
```

Variables (`.env`):
- `DEFAULT_MAX_ACTIVE_CHATS` — default when a bot JSON omits `max_active_chats`.
- `TELEGRAM_MODE` — `webhook` | `poll`.
- `TELEGRAM_API_BASE`, `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_PATH`, `TELEGRAM_WEBHOOK_SECRET`.
- `CORS_ALLOWED_ORIGINS`.
- `BOTS_CONFIG_PATH` — optional override for the bots credentials file (default:
  `backend/app/config/bots.json`).

## Trade-offs & assumptions

- **Bot `username` is unique** — each registered bot has a distinct Telegram
  `@username`; the repository indexes by it and API routes use
  `/bots/{username}/...`, so duplicates are not supported.
- **In-memory persistence** — state resets on restart, which the brief allows
  (session-scoped). The store's async interface is the swap point for a DB.
- **Inline delivery** — `POST /bots/{username}/chats/{chat_id}/messages` awaits
  Telegram and returns the final status. The planned queue/worker split
  `pending` immediately and rely on the WS receipt; the client already supports
  that, so the change is backend-only.
- **Conversation limit is config** — `MAX_ACTIVE_CHATS` (default 1) caps active
  conversations; the model is multi-ready (messages and routing are keyed by
  `chat_id`), so raising it needs no code change.
- **Store-first, broadcast when connected** — incoming messages are always
  persisted (subject to active-chat capacity). WebSocket `{type:"message"}` is
  sent only when at least one agent client is connected; otherwise the agent
  discovers stored messages on the next REST load.
- **`read_at` per message** — agent read state is stored on each message
  (`read_at: null` = unread for incoming user messages). Mark-read is
  `POST /bots/{username}/chats/{chat_id}/messages/read` with a `read_at`
  timestamp.
- **`POST /reset` is unauthenticated** — it's a dev/test affordance; a real
  deployment would put auth in front of it (or omit it).

### Unread badges: prefetch vs server `unread_count`

`active_chats` on `GET /bots` is computed server-side and does not require
loading messages. **Unread** is separate: the rule is
`count(user messages where read_at is null)` per thread (summed for bot badges).

| Approach | How it works | Trade-off |
|---|---|---|
| **Prefetch (current)** | Client calls `GET /bots/{username}/chat-summaries` then `GET /bots/{username}/chats/{chat_id}/messages` for every active thread; frontend counts `read_at` in `messagesByThread` | Simple — no new list fields; correct whenever histories are loaded. Costly on inbox open (`1 + N` requests, full text for all threads). |
| **Server `unread_count` (recommended next)** | Add `unread_count` to `ChatSummary` and optionally `BotInboxItem`; maintain or query on store/mark-read | Badges on app open with one list request; prefetch only the thread the agent opens. Extra server logic (count on insert + mark-read, or aggregate query). |

We use **prefetch today** for a small assignment scope. **`unread_count` on list
endpoints** is the better long-term fit when chat volume or history length grows.
`read_at` on messages stays either way — it drives mark-read and thread history;
counts are a denormalized convenience for the sidebar.

## Working locally

### Prerequisites

- Python 3.10+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- (Optional) [ngrok](https://ngrok.com/) or similar if you want webhook mode locally

### One-time setup

All environment files live at the **repo root** (not inside `backend/`). The app
loads them automatically when you run uvicorn from `backend/`.

```bash
# From the repo root
cp .env.example .env
cp .env.development.example .env.development   # recommended for local dev
cp backend/app/config/bots.json.example backend/app/config/bots.json
```

Edit `backend/app/config/bots.json` — set each bot's `token` (and optional
`max_active_chats`). The `bot_id` in the file must match the numeric id returned
by Telegram `getMe` on startup.

Edit `.env.development` to use polling (no public URL required):

```bash
TELEGRAM_MODE=poll
```

Real shell environment variables override both `.env` files.

### Install dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run the server

Always run from `backend/` with the virtualenv active:

| Mode | Command | When to use |
|---|---|---|
| **Polling** (recommended locally) | `ENVIRONMENT=development uvicorn app.main:app --reload` | No tunnel needed; uses `getUpdates` long-poll |
| **Webhook** | `uvicorn app.main:app --reload` | Needs `TELEGRAM_WEBHOOK_URL` pointing at a public HTTPS tunnel |

Health check: [http://localhost:8000/health](http://localhost:8000/health)

In webhook mode each bot is registered to:

```text
{TELEGRAM_WEBHOOK_URL}{TELEGRAM_WEBHOOK_PATH}/{bot_id}
```

### Typical local workflow

Use polling on the backend and the real frontend (see [`frontend.md`](./frontend.md)):

```bash
# Terminal 1 — backend
cd backend && source venv/bin/activate
ENVIRONMENT=development uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open the inbox at [http://localhost:5173](http://localhost:5173). Message your
bot from Telegram at any time — incoming messages are stored even if the inbox
is closed. Connect the WebSocket (open the app) for live updates; otherwise
select the bot and conversation to load stored history via REST.

### Automated tests

From `backend/` with the virtualenv active:

```bash
python -m pytest tests/ -q
```

- **`tests/test_api_e2e.py`** — REST E2E via `httpx.ASGITransport` (health, bots, send, mark-read).
- **`tests/test_webhook_e2e.py`** — Telegram webhook path + secret middleware + persistence.
- **`tests/test_chat_service.py`** — domain `ChatService` sunny paths and errors (fake `MessageProvider`).
- **`tests/test_telegram_provider_http.py`** — `TelegramProvider` → `TelegramClient` HTTP mocked with **respx** (`sendMessage`, `getMe`).

`app/factory.py` builds the ASGI app for tests **without** lifespan (no real Telegram listeners). Each test gets a fresh `AppContext`; `routes/api.py` builds a **new** `APIRouter` per `app_router(deps)` so multiple apps in one process do not share stale dependency closures.

