# Frontend — implementation overview

A React (Vite) single-page app that renders the chat between the Telegram bot
and the remote participant. This document describes what was built; see
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
  main.jsx                  React entry (StrictMode)
  App.jsx                   Router: /, /bots/:botUsername, /bots/:botUsername/chats/:chatId
  config.js                 API_URL, WS_URL, USE_MOCK (from VITE_* env)
  api/
    client.js               REST: fetchBots, fetchBotConversations, fetchHistory, sendMessage, resetChat
  hooks/
    useWebSocket.js         Generic self-healing WebSocket (reconnect / backoff)
    useInbox.js             Thin orchestrator: useReducer, effects, send/reset, WS dispatch
  inbox/                    Inbox state machine (reducer + helpers)
    state.js                Initial state shape
    reducer.js              Action handlers (BOTS_LOADED, WS_EVENT, SEND_OPTIMISTIC, …)
    websocket.js            applyWebSocketEvent — maps server events to state updates
    messages.js             Thread append + status updates
    conversations.js        Conversation list merge / upsert
    unread.js               Unread counts derived from message read_at
    selectors.js            selectMessages, selectConversations, selectConversation
    keys.js                 threadKey(botUsername, chatId)
    normalize.js            Message / conversation normalization
    mock.js                 Mock-mode fixtures (wraps __mocks__/seedMessages.js)
    prefetch.js             Loads conversation list + per-thread history for unread badges
  pages/
    InboxPage.jsx           Three-column shell: bots → conversations → chat
  components/
    BotList.jsx             Bot sidebar + unread badges
    ConversationList.jsx    Conversation sidebar + unread badges
    Chat.jsx                Thread panel (header, list, composer)
    ChatHeader.jsx          Panel title
    ConnectionStatus.jsx    Live socket status indicator
    MessageList.jsx         Scrollable list + auto-scroll
    Message.jsx             Single bubble (side + delivery ticks)
    MessageInput.jsx        Composer (Enter or button)
  utils/
    time.js                 formatMessageTime, formatConversationTime
  index.css                 Styles

frontend/__mocks__/
  seedMessages.js           Sample bots / conversations / messages for mock mode
```

Dependency direction is one-way:

```
App → InboxPage → components (props only)
InboxPage → useInbox → { inboxReducer, api/client, useWebSocket }
inboxReducer → { websocket, messages, conversations, unread, selectors, … }
```

`InboxPage` owns navigation (react-router `useParams` / `useNavigate`). Components
are presentational; network and state logic live in `useInbox` and the `inbox/`
reducer modules.

## Data flow

### Outgoing (agent → Telegram user)

1. `useChat.send(text)` generates an `id` and appends an **optimistic** message
   (`sender:"agent"`, `status:"pending"`) — it shows instantly.
2. `POST /bots/{username}/chats/{chat_id}/messages` with `{ id, text, timestamp }`.
   The server stores it and echoes it back; the client adopts the status. On failure
   (incl. a `409` for an inactive chat) the message flips to `"failed"`.
3. A later WebSocket `receipt` event updates the same id to `sent`/`failed`.

### Incoming (Telegram user → agent)

1. The server stores the message, then pushes `{ type: "message", bot_username, … }`
   over the WebSocket when an agent client is connected.
2. `useInbox` appends live events via the reducer. If the inbox was closed when
   the message arrived, the agent sees it after selecting the bot/conversation
   and loading history from REST. Ordering is the server's; the client never
   re-sorts.

A `{ type: "reset" }` event (from the admin Reset button) drops the client back
to the no-chat state.

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

- **Session-scoped, no client persistence.** History is loaded when a thread is
  opened; the brief allows the chat to show only the current session. A DB added
  server-side would surface through the same `GET /bots/{username}/messages`
  call.
- **Bot cannot initiate a conversation ("no chat yet").** A Telegram bot only
  learns a `chat_id` after the remote user messages it — the agent cannot pick
  an arbitrary id and start chatting. The UI reflects this: send is enabled only
  when a conversation is selected in the URL (`canSend = chatId != null`). Until
  then the composer is disabled with *"Waiting for a user to start the chat…"*.
  New threads appear when `GET /bots/{username}/conversations` returns them
  (e.g. after the user messaged while the inbox was closed) or when a live
  WebSocket `message` arrives. There is no flow to message an unknown `chat_id`.
- **Client-generated ids.** Chosen for race-free correlation across the
  optimistic bubble, REST response, and WebSocket receipt. The server treats the
  id as the storage key and is expected to reject duplicates.

### Unread badges: prefetch vs server `unread_count`

`read_at` on each message is the source of truth for read state (server-persisted;
the client calls `POST .../messages/read` when a thread is opened). Badge
numbers are derived client-side today: count user messages with `read_at == null`
in `messagesByThread`.

Because conversation summaries do not include `read_at`, the client **prefetches
full history** for every active thread when bots/conversations load
(`inbox/prefetch.js`). Capacity labels (`active_chats` / `max_chats`) already
come from `GET /bots` and do not depend on prefetch.

See the full comparison in [`backend.md`](./backend.md#unread-badges-prefetch-vs-server-unread_count).

| Approach | Pros | Cons |
|---|---|---|
| **Prefetch (today)** | No extra API fields; reuses `GET /messages`; stays in sync with `read_at` | `1 + N` requests and full message payloads on inbox open |
| **Server `unread_count` (planned)** | List endpoints return counts; badges work immediately; load only the open thread | Server must compute or maintain counts on store/read |

## Working locally

### Prerequisites

- Node.js 18+
- A running backend (see [`backend.md`](./backend.md)), **or** use mock mode with
  no backend at all

### Install dependencies

```bash
cd frontend
npm install
```

### Environment variables

Vite reads these at dev/build time. Set them inline or in `frontend/.env.local`:

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend REST base URL; WebSocket URL is derived (`http` → `ws`) |
| `VITE_USE_MOCK` | (unset / `false`) | Set to `true` to run with seeded sample data and no backend |

`CORS_ALLOWED_ORIGINS` on the backend must include the Vite origin
(`http://localhost:5173` by default).

### Run the dev server

| Script | Command | When to use |
|---|---|---|
| **Dev** (real backend) | `npm run dev` | Default — talks to `http://localhost:8000` |
| **Dev mock** (no backend) | `npm run dev:mock` | UI only; seeded bots, conversations, and messages |
| **Custom backend URL** | `VITE_API_URL=http://localhost:8000 npm run dev` | Point at a different host/port |
| **Production build** | `npm run build` | Output to `frontend/dist/` |
| **Preview build** | `npm run preview` | Serve the production bundle locally |

App URL: [http://localhost:5173](http://localhost:5173)

### Typical local workflow

**With a live backend** — start the backend first (polling mode is easiest; see
backend docs), then:

```bash
cd frontend && npm run dev
```

Navigate to a bot (`/bots/{username}`), pick a conversation, and send messages.
The connection indicator shows WebSocket status; incoming Telegram messages
arrive over `/ws`.

**Without a backend** — useful for UI work only:

```bash
cd frontend && npm run dev:mock
```

Mock mode seeds multiple bots and conversations locally. Replies are echoed in
the UI but nothing is sent to Telegram.

### Full stack (two terminals)

```bash
# Terminal 1 — backend (polling)
cd backend && source venv/bin/activate
ENVIRONMENT=development uvicorn app.main:app --reload

# Terminal 2 — frontend
cd frontend && npm run dev
```
