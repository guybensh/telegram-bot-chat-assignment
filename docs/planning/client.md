# Client — planning

## What it is

A React.js single-page application that renders a real-time chat interface between the user and a remote Telegram participant.

## Responsibilities

- Display the full message history for the current session
- Allow the user to type and send messages
- Reflect incoming messages in real time without a page refresh
- Show delivery/error state per message (sent, failed)
- Visually distinguish outgoing (user) vs incoming (Telegram participant) messages

## Why these choices

### Sending messages — REST POST

Outgoing messages are sent via `POST /messages`. HTTP gives us an immediate response so the UI can confirm the message was accepted or surface an error without any extra logic. Simple, stateless, easy to retry.

### Receiving messages — WebSocket

The client opens a single persistent WebSocket connection on load. The server uses this channel to push anything it needs the client to know asynchronously:

- Incoming messages from the Telegram participant
- Delivery receipts (`{type: "receipt", message_id, status}`)
- Future: typing indicators, error events

Keeping the WebSocket as a general server-push channel means adding new event types costs nothing on the transport layer — the frontend just handles a new `type` value.

### No persistent client-side storage

The assignment scopes the chat to the current session. Message history is loaded from the server on mount and kept in component state. If the DB layer is added server-side, the same load-on-mount call will automatically reflect full history with no client changes needed.

## Key decisions to document

- The WebSocket connection should reconnect automatically on drop (exponential backoff)
- Optimistic UI: show the message immediately on send, mark as failed if the POST returns an error
- Message ordering is owned by the server — the client renders in the order received, never re-sorts
