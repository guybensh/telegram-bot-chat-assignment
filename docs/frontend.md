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

## Message model

Every message — incoming or outgoing — is the same shape, keyed by a single
`id`:

```js
{
  id:        "uuid",                       // client-generated for outgoing,
                                           // server-generated for incoming
  text:      "Hello",
  timestamp: "2026-06-12T09:30:00.000Z",   // ISO 8601; set at send time, used for ordering
  sender:    "user" | "bot",               // "user" = us, "bot" = Telegram bot
  status:    "pending" | "sent" | "failed" // outgoing
             | "received",                 // incoming (constant)
}
```

- **`id`** — generated on the client at send time so the optimistic bubble, the
  server record, and any later receipt all share one identity. The server
  stores outgoing messages under this id. Incoming messages bring their own id.
- **`sender`** drives the bubble side/color (`user` → right/blue,
  `bot` → left/white) via the `outgoing`/`incoming` CSS classes.
- **`status`** drives the delivery indicator, shown only on our own messages.

## Data flow

### Outgoing (user → Telegram)

1. `useChat.send(text)` generates an `id` and appends an **optimistic** message
   with `status: "pending"` — it shows instantly.
2. `POST /messages` with the **full message object**. The server stores it
   verbatim (using the `timestamp` to order the conversation) and echoes it
   back; the client adopts any status it reports. On failure the message flips
   to `"failed"`.
3. A later WebSocket `receipt` event updates the same id to `sent`/`failed`.

### Incoming (Telegram → user)

1. The server pushes `{ type: "message", ... }` over the WebSocket.
2. `useChat` appends it to the list. Ordering is the server's; the client never
   re-sorts — it renders in arrival order.

## Backend contract

| Channel | Endpoint | Payload |
|---|---|---|
| Load history | `GET /messages` | → array of messages |
| Send | `POST /messages` | full message object → the stored message |
| Server push | WebSocket `/ws` | `{ type: "message", ... }` / `{ type: "receipt", message_id, status }` |

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
- **Single conversation.** The UI assumes one bot ↔ one participant, matching
  the single-active-chat backend constraint; there is no conversation list.
- **Client-generated ids.** Chosen for race-free correlation across the
  optimistic bubble, REST response, and WebSocket receipt. The server treats the
  id as the storage key and is expected to reject duplicates.
