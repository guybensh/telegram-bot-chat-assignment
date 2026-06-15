# Integration — cross-layer contract

How the React inbox, FastAPI backend, and Telegram connect. Flows and wire
protocols only — see [`backend.md`](./backend.md) and [`frontend.md`](./frontend.md)
for tier-specific detail.

## Actors

| Actor | Role |
|---|---|
| **Agent client** (React) | Inbox UI — lists bots/chats, sends replies, receives push events |
| **Backend** (FastAPI) | Domain logic, persistence, bridges Telegram ↔ agent |
| **Telegram** | External provider — delivers user messages in; carries bot replies out |

All agent-facing traffic is scoped by **bot** (`username`) and **chat** (`chat_id`).

## Protocol decisions

| Path | Protocol | Why |
|---|---|---|
| Agent → backend | **REST** | Client-initiated; explicit HTTP status (e.g. `409` when chat is not active) |
| Backend → agent | **WebSocket** (`/ws`) | Server-initiated push — new messages, send receipts, reset |
| Backend → Telegram (out) | **HTTPS** (`sendMessage`) | Inline on send — POST awaits delivery, no async worker queue |
| Telegram → backend (in) | **Webhook** (default) or **long poll** (`getUpdates`) | Webhook: Telegram pushes a short HTTP POST per update. Poll: one long-lived outbound connection per bot. Both converge on the same handler |

**Store-first incoming** — user messages are always persisted before any WebSocket
broadcast. If no agent is connected, the client loads them later over REST.

**Single message shape** — the same `Message` fields in REST responses and
WebSocket payloads (below).

## Outgoing flow — agent → Telegram user

```
Agent UI ──POST …/messages──► Backend ──sendMessage──► Telegram ──► remote user
                │                                      │
                ◄── Message (final status) ────────────┘
                │
Backend ──receipt on /ws──► Agent UI (and any other connected clients)
```

1. Client shows an optimistic message (`sender: "agent"`, `status: "pending"`).
2. `POST /bots/{username}/chats/{chat_id}/messages`.
3. Backend rejects with `409` if the chat is not active (user must message the bot first).
4. Backend stores, calls Telegram `sendMessage`, sets `sent` or `failed`, returns `Message`.
5. Backend broadcasts `{ type: "receipt", … }`.

## Incoming flow — Telegram user → agent

```
Remote user ──► Telegram ──► Backend ──store──► (if agent connected) ──/ws──► Agent UI
                    ▲              │
                    │              └── webhook POST  or  getUpdates poll
                    └── sendMessage (outgoing path above)
```

1. User messages the bot in Telegram.
2. Update arrives via **webhook** (`POST /telegram/webhook/{bot_id}`) or **poll**
   (`getUpdates` loop) — parsed by `MessageProvider`, handled by `ChatService`.
3. Backend admits the chat (capacity limit), stores
   `{ sender: "user", status: "received", read_at: null }`.
4. If an agent client is connected — `{ type: "message", … }` on `/ws`.
   Otherwise the message waits for REST load.

## Inbox sync flow — agent catches up

When the agent opens the inbox or a thread:

```
GET …/chat-summaries  →  preview rows (last message snippet per active chat)
GET …/chats/{chat_id}/messages  →  full thread (includes read_at for unread badges)
POST …/messages/read  →  when a thread is opened (or live message while viewing it)
```

Unread is derived from `read_at` on stored messages; mark-read is REST only.
