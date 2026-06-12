# Frontend — implementation overview

A React (Vite) single-page app that renders the chat between the Telegram bot
and the remote participant. This document describes what was built; see
[`client.md`](./client.md) for the original planning rationale and
[`integration.md`](./integration.md) for the cross-layer contract.

## Design goals

- **Clear separation of concerns** — transport, state, and presentation are
  independent layers, so any one can change without touching the others.
- **Real-time in, request/response out** — incoming messages arrive over a
  WebSocket; outgoing messages go over REST and confirm via that same socket.
- **Swappable backend** — the client codes against a small, documented contract,
  so the in-memory backend can later become a database-backed one with no
  frontend changes.

## Structure

```
src/
  config.js                 Backend URLs + feature flags (from VITE_* env)
  api/
    client.js               REST layer: fetchHistory(), sendMessage(id, text)
  hooks/
    useWebSocket.js         Generic, self-healing WebSocket (reconnect/backoff)
    useChat.js              Chat state: history, optimistic send, receipts
  components/
    ChatHeader.jsx          Title + connection indicator
    ConnectionStatus.jsx    Live "Connecting / Connected / Reconnecting" dot
    MessageList.jsx         Scrollable list + auto-scroll + empty state
    Message.jsx             A single bubble (side + delivery ticks)
    MessageInput.jsx        Composer (Enter or button, ignores empty)
  mocks/
    seedMessages.js         Sample conversation for mock mode only
  App.jsx                   Composition root (no logic)
  index.css                 Styles
```

The dependency direction is one-way: `App → components → (props)` and
`App → useChat → { useWebSocket, api/client }`. Components are presentational
and hold no network logic; all state lives in `useChat`.

## Roles & message model

This app is a **back-office console**: a human **agent** holds a Telegram
conversation with a remote **user**, with the bot as the conduit.

Every message is the same shape:

```js
{
  id:        "uuid",                       // client-gen for outgoing, server-gen for incoming
  chat_id:   123456,                       // the Telegram conversation it belongs to
  text:      "Hello",
  timestamp: "2026-06-12T09:30:00.000Z",   // ISO 8601; set at send time, used for ordering
  sender:    "user" | "agent" | "bot",
  status:    "pending" | "sent" | "failed" // outgoing
             | "received",                 // incoming (constant)
}
```

- **`sender`** — `user` = the remote Telegram human (incoming, left); `agent` =
  us, the back-office human (outgoing, right); `bot` = a future automated reply
  (reserved). Rendering: `sender !== "user"` is our side, so `agent` and `bot`
  both render on the right.
- **`chat_id`** — the conversation. The server owns it (it's the Telegram user's
  chat); the client learns it and replies into it — it never invents one.
- **`id`** — client-generated on send so the optimistic bubble, the server
  record, and any receipt share one identity. Incoming messages bring their own.
- **`status`** — drives the delivery indicator, shown only on our own messages.

## Conversations & the "no chat yet" state

A Telegram **bot cannot initiate** a conversation — it only learns a `chat_id`
once the user messages it. So:

- On mount the client calls `GET /conversations`; if one exists it loads its
  history and sets the active `chatId`.
- Otherwise `chatId` is `null` and the composer is **disabled** ("Waiting for a
  user to start the chat…"). The client also learns the `chat_id` live from the
  first incoming `message` event.
- `canSend = chatId != null` gates the composer; sends include that `chat_id`.

## Data flow

### Outgoing (agent → Telegram user)

1. `useChat.send(text)` generates an `id` and appends an **optimistic** message
   (`sender:"agent"`, `status:"pending"`) — it shows instantly.
2. `POST /messages` with the **full message object** (including `chat_id`). The
   server stores it and echoes it back; the client adopts the status. On failure
   (incl. a `409` for an inactive chat) the message flips to `"failed"`.
3. A later WebSocket `receipt` event updates the same id to `sent`/`failed`.

### Incoming (Telegram user → agent)

1. The server pushes `{ type: "message", chat_id, ... }` over the WebSocket.
2. `useChat` appends it (and adopts `chat_id` if it didn't have one). Ordering is
   the server's; the client never re-sorts.

A `{ type: "reset" }` event (from the admin Reset button) drops the client back
to the no-chat state.

## Backend contract

| Channel | Endpoint | Payload |
|---|---|---|
| List conversations | `GET /conversations` | → `[{ chat_id }]` |
| Load history | `GET /messages?chat_id=<id>` | → array of messages |
| Send | `POST /messages` | `{ id, chat_id, text, timestamp }` → the stored message |
| Server push | WebSocket `/ws` | `{type:"message", ...}` / `{type:"receipt", message_id, chat_id, status}` / `{type:"reset"}` |
| Admin reset | `POST /admin/reset` | clears all conversations (dev/admin) |

The WebSocket is a general server-push channel — new event types are just
another `case` in `useChat`'s handler, no transport changes.

## Connectivity & resilience

- `useWebSocket` reconnects automatically with exponential backoff (1s → 30s),
  and survives React StrictMode's double-mount in development.
- `ConnectionStatus` reflects the live socket state so the user knows whether
  incoming messages can currently arrive.

## Configuration

- `VITE_API_URL` — backend base URL (default `http://localhost:8000`). The
  WebSocket URL is derived from it (`http→ws`, `https→wss`).
- `VITE_USE_MOCK` — when `true`, the app runs with **no backend**: it seeds a
  sample conversation and echoes replies locally. Run with `npm run dev:mock`.
  Mock logic is isolated to a fixture file plus a couple of guarded branches, so
  it imposes nothing on the real data path.

## Scripts

```bash
npm run dev        # dev server against the real backend
npm run dev:mock   # dev server with mock data, no backend needed
npm run build      # production build
```

## Trade-offs & assumptions

- **Session-scoped, no client persistence.** History is loaded on mount; the
  brief allows the chat to show only the current session. A DB added
  server-side would surface through the same `GET /messages` call.
- **Single conversation.** The UI shows the one active conversation, matching
  the backend's single-active-chat policy; there's no conversation switcher yet,
  but messages are already tagged with `chat_id` so one could be added.
- **Client-generated ids.** Chosen for race-free correlation across the
  optimistic bubble, REST response, and WebSocket receipt. The server treats the
  id as the storage key and is expected to reject duplicates.
