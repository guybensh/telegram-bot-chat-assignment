# Server — planning

## What it is

A FastAPI (Python) backend that manages WebSocket connections, a Telegram bot instance, message queuing, and persistence.

## Responsibilities

- Maintain a WebSocket connection per connected client
- Accept outgoing messages via REST and enqueue them for the bot worker
- Receive incoming Telegram messages and push them to the correct client
- Enforce the single-active-chat constraint (one Telegram contact per user)
- Persist messages and session state to a database

## Why these choices

### WebSocket connection map

The server keeps an in-memory map of `user_id → WebSocket`. Any server-initiated event (incoming message, receipt, error) is resolved through this map. At scale this moves to a shared store (Redis) so multiple FastAPI instances can route correctly, but the interface stays the same.

### Outgoing queue

Messages are not sent to Telegram inline with the POST handler. Instead the handler writes to a queue and returns immediately. The bot worker consumes the queue independently. This decouples the HTTP response time from Telegram API latency, gives us a natural retry point, and prevents burst traffic from blocking the server.

### Incoming queue + dispatcher

Telegram pushes incoming messages to a webhook endpoint. These are written to an incoming queue and processed by a dispatcher that resolves `telegram_chat_id → user_id → WebSocket` and pushes the event to the correct client. The queue ensures no messages are dropped if the dispatcher is momentarily busy.

### Database

Two core tables:

- `sessions` — maps `user_id` to `telegram_chat_id`. Enforces the one-active-chat constraint and survives restarts.
- `messages` — stores every message with direction (`in`/`out`), text, timestamp, and status. Enables history reload on reconnect.

Starting with SQLite is fine for the assignment. The schema and access layer should be written against an abstraction (SQLAlchemy) so swapping to Postgres requires no logic changes.

### Single-active-chat enforcement

On first contact from a Telegram user, the backend registers that `chat_id` against the session. All subsequent Telegram messages from unknown `chat_id`s are silently dropped. This is a policy decision — at scale it becomes a per-user pairing, but the enforcement point stays the same.

## Key decisions to document

- Bot can run in polling mode for local dev, webhook mode for production
- Message ordering is assigned server-side via timestamp at insertion — the client never reorders
- All Telegram API calls are async and wrapped with error handling so a Telegram outage doesn't crash the server
