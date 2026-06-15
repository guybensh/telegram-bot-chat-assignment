# High-level architecture

Bird's-eye view of the system. For wire protocols and step-by-step flows see
[`integration.md`](./integration.md); for tier detail see [`backend.md`](./backend.md)
and [`frontend.md`](./frontend.md).

## System context

```mermaid
flowchart TB
  subgraph Agent["Agent client — React (Vite)"]
    Inbox["Inbox UI\nbots → chats → thread"]
    Hook["useInbox + inbox reducer"]
    RestC["api/client.js"]
    WsC["useWebSocket"]
    Inbox --> Hook
    Hook --> RestC
    Hook --> WsC
  end

  subgraph Backend["Backend — FastAPI"]
    direction TB
    Api["routes/api.py\nREST + WebSocket /ws"]
    Wh["routes/webhook.py\nPOST /telegram/webhook/{bot_id}"]
    Lst["listeners/\nWebhookListener | PollingListener"]
    CS["ChatService"]
    BS["BotService"]
    Repo[("Repositories\nChatRepository · BotRepository\n(in-memory)")]
    CM["ConnectionManager"]
    TP["TelegramProvider\n+ TelegramClient"]

    Api --> CS
    Api --> BS
    Wh --> CS
    Lst --> CS
    CS --> Repo
    BS --> Repo
    CS --> CM
    CS --> TP
    CM --> Api
  end

  subgraph Telegram["External — Telegram"]
    TAPI["Bot API\nsendMessage · getUpdates · setWebhook"]
    TUser["Remote user\n(Telegram app)"]
  end

  RestC -->|"REST\nGET chat-summaries · messages\nPOST send · mark-read"| Api
  WsC <-->|"WebSocket /ws\nmessage · receipt · reset"| Api

  TP -->|"HTTPS sendMessage"| TAPI
  TAPI -->|"webhook POST"| Wh
  TAPI -->|"getUpdates long poll"| Lst
  TUser <-->|"Telegram chat"| TAPI
```

## Message flows

```mermaid
flowchart LR
  subgraph Out["Outgoing — agent → user"]
    direction LR
    A1["Agent UI"] -->|"POST …/chats/{id}/messages"| B1["ChatService"]
    B1 -->|"sendMessage"| T1["Telegram"]
    B1 -->|"HTTP Message"| A1
    B1 -->|"WS receipt"| A1
    T1 --> U1["Remote user"]
  end

  subgraph In["Incoming — user → agent"]
    direction LR
    U2["Remote user"] --> T2["Telegram"]
    T2 -->|"webhook or poll"| B2["ChatService"]
    B2 -->|"store"| S2[("Repository")]
    B2 -->|"WS message\n(if agent connected)"| A2["Agent UI"]
    B2 -.->|"else REST on open"| A2
  end

  subgraph Sync["Inbox sync — agent catches up"]
    direction LR
    A3["Agent UI"] -->|"GET chat-summaries"| B3["ChatService"]
    A3 -->|"GET …/messages"| B3
    A3 -->|"POST …/messages/read"| B3
    B3 --> S3[("Repository")]
  end
```

## Layer responsibilities

| Layer | Responsibility |
|---|---|
| **Agent client** | Three-column inbox; optimistic send; live updates over `/ws`; unread from `read_at` |
| **routes/** | Thin HTTP/WS adapters — validate input, map errors, delegate to services |
| **ChatService** | Single orchestrator — send/receive, capacity, store-first incoming, broadcast gate |
| **Repositories** | Per-bot chat/message storage behind async interfaces |
| **TelegramProvider** | Parse incoming updates; deliver outgoing `sendMessage` |
| **Listeners / webhook** | Two ingress paths (poll vs webhook) into the same `ChatService` handler |
| **ConnectionManager** | Tracks connected agents; broadcasts push events on `/ws` |
| **Telegram** | External messaging provider — not owned by this codebase |

## Protocol summary

| Direction | Protocol |
|---|---|
| Agent → backend | REST |
| Backend → agent | WebSocket (`/ws`) |
| Backend → Telegram | HTTPS (`sendMessage`) |
| Telegram → backend | Webhook POST **or** `getUpdates` long poll |
