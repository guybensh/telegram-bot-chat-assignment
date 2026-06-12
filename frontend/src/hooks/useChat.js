import { useCallback, useEffect, useState } from "react";
import { USE_MOCK, WS_URL } from "../config";
import { fetchHistory, sendMessage } from "../api/client";
import { useWebSocket } from "./useWebSocket";
import { seedMessages } from "../mocks/seedMessages";

/**
 * Owns the chat's message list and the rules for mutating it.
 *
 * Ordering policy: the server is the single source of truth for ordering. We
 * append in the order events arrive and never re-sort. Outgoing messages are
 * shown optimistically and then reconciled with the server's canonical record.
 *
 * Returns { messages, connectionStatus, send }.
 */
export function useChat() {
  const [messages, setMessages] = useState(USE_MOCK ? seedMessages : []);

  // Load the current session's history once on mount. When a DB is added
  // server-side, this same call transparently returns full history. Skipped in
  // mock mode, which seeds its history directly above.
  useEffect(() => {
    if (USE_MOCK) return undefined;
    let cancelled = false;
    fetchHistory()
      .then((history) => {
        if (!cancelled) setMessages(history.map(normalize));
      })
      .catch((err) => console.error("Could not load history", err));
    return () => {
      cancelled = true;
    };
  }, []);

  // Handle every server-pushed event. New event types only add a branch here.
  const handleEvent = useCallback((event) => {
    switch (event.type) {
      case "message":
        setMessages((prev) => [...prev, normalize(event)]);
        break;
      case "receipt":
        setMessages((prev) =>
          prev.map((m) =>
            m.id === event.message_id ? { ...m, status: event.status } : m
          )
        );
        break;
      default:
        console.warn("Unhandled WebSocket event type:", event.type);
    }
  }, []);

  const connectionStatus = useWebSocket(WS_URL, handleEvent, !USE_MOCK);

  const send = useCallback(async (text) => {
    // The client generates the id so the optimistic bubble, the server record,
    // and any later receipt all share one stable identity. The server stores
    // the message under this id.
    const id = crypto.randomUUID();
    const optimistic = {
      id,
      text,
      timestamp: new Date().toISOString(),
      sender: "user",
      status: "pending",
    };
    setMessages((prev) => [...prev, optimistic]);

    // Mock mode: no backend. Mark the message sent, then echo a fake reply so
    // both bubble styles and the optimistic flow are visible locally.
    if (USE_MOCK) {
      setTimeout(() => updateStatus(setMessages, id, "sent"), 300);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            text: `Echo: ${text}`,
            timestamp: new Date().toISOString(),
            sender: "bot",
            status: "received",
          },
        ]);
      }, 1200);
      return;
    }

    try {
      // Send the full message object; the server stores it verbatim (timestamp
      // for ordering, sender, status) and echoes it back.
      const saved = await sendMessage(optimistic);
      if (saved?.status) {
        updateStatus(setMessages, id, saved.status);
      }
    } catch (err) {
      console.error("Send failed", err);
      updateStatus(setMessages, id, "failed");
    }
  }, []);

  return { messages, connectionStatus, send };
}

// Set the delivery status of the message identified by id.
function updateStatus(setMessages, id, status) {
  setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status } : m)));
}

// Normalize a server message into the client's shape. Every message — incoming
// or outgoing — is keyed by its single `id`.
function normalize(msg) {
  return {
    id: msg.id,
    text: msg.text,
    timestamp: msg.timestamp,
    sender: msg.sender,
    status: msg.status,
  };
}
