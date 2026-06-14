# Integration — planning

## What it is

How the client, server, and Telegram connect end-to-end. This document covers the two message flows, the contract between layers, and the protocol decisions that tie them together.

## Outgoing flow — user sends a message

```
Client → POST /messages → FastAPI → outgoing queue → bot worker → Telegram API → remote participant
```

1. User hits send in the UI
2. Client fires `POST /messages` with `{text, session_id}`
3. FastAPI validates, writes to DB with status `pending`, enqueues the job, returns `201`
4. Bot worker dequeues, calls Telegram `sendMessage`, updates DB status to `sent`
5. Server pushes a receipt event to the client over WebSocket: `{type: "receipt", message_id, status: "sent"}`
6. UI updates the message indicator (e.g. ✓)

Error path: if the bot worker fails after N retries, it updates status to `failed` and pushes `{type: "receipt", status: "failed"}` so the UI can surface a retry option.

## Incoming flow — remote participant sends a message

```
Remote participant → Telegram API → webhook → FastAPI → incoming queue → dispatcher → WebSocket → client
```

1. Remote participant sends a message in Telegram
2. Telegram calls the registered webhook endpoint
3. FastAPI validates the Telegram token, writes the message to DB, enqueues it
4. Dispatcher resolves `telegram_chat_id → user_id → WebSocket`
5. Pushes `{type: "message", text, timestamp, direction: "in"}` to the client
6. UI appends the message to the chat

## Protocol split — why

| Direction | Protocol | Reason |
|---|---|---|
| User → server | REST POST | Client-initiated, needs explicit confirmation, trivial error handling |
| Server → client | WebSocket | Server-initiated, async, single persistent channel for all push events |

The WebSocket is a general server-push channel, not just for chat messages. Receipts and future events (typing indicators, errors) all travel the same pipe as new event types — no transport changes needed.

## Local development vs production

| Concern | Local | Production |
|---|---|---|
| Telegram updates | Long polling | Webhook (HTTPS required) |
| Queue | In-memory / asyncio.Queue | Redis |
| Database | SQLite | Postgres |
| Multiple instances | Single process | Shared Redis for WS map + queues |

## Key decisions to document

- Webhook URL must be registered with Telegram via `setWebhook` — this requires a public HTTPS endpoint (use ngrok locally)
- Bot tokens live in `backend/app/config/bots/*.json` on the server and are never exposed to the client
- Message IDs are generated server-side so receipts can be correlated correctly across the WebSocket and REST response
