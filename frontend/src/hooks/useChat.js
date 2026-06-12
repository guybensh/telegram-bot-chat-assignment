import { useCallback, useEffect, useState } from "react";
import { USE_MOCK, WS_URL } from "../config";
import {
  fetchConversations,
  fetchHistory,
  resetChat,
  sendMessage,
} from "../api/client";
import { useWebSocket } from "./useWebSocket";
import { seedMessages, MOCK_CHAT_ID } from "../mocks/seedMessages";

/**
 * Owns the chat's message list, the active conversation, and the rules for
 * mutating them.
 *
 * The conversation (`chatId`) is owned by the server: it's the Telegram
 * participant's chat, learned only when that participant messages the bot. The
 * client discovers it (via GET /conversations on load, or the first incoming
 * message event) and replies into it — it never invents one.
 *
 * Ordering policy: the server is the source of truth; we append in arrival
 * order and never re-sort. Outgoing messages render optimistically.
 *
 * Returns { messages, connectionStatus, send, canSend }.
 */
export function useChat() {
  const [messages, setMessages] = useState(USE_MOCK ? seedMessages : []);
  // The active conversation. null until a participant has started one — which
  // is exactly when the agent is allowed to send.
  const [chatId, setChatId] = useState(USE_MOCK ? MOCK_CHAT_ID : null);

  // On mount, discover the active conversation and load its history. Skipped in
  // mock mode, which seeds a conversation directly above.
  useEffect(() => {
    if (USE_MOCK) return undefined;
    let cancelled = false;
    fetchConversations()
      .then((conversations) => {
        if (cancelled || conversations.length === 0) return undefined;
        const id = conversations[0].chat_id;
        setChatId(id);
        return fetchHistory(id).then((history) => {
          if (!cancelled) setMessages(history.map(normalize));
        });
      })
      .catch((err) => console.error("Could not load conversations", err));
    return () => {
      cancelled = true;
    };
  }, []);

  // Handle every server-pushed event. New event types only add a branch here.
  const handleEvent = useCallback((event) => {
    switch (event.type) {
      case "message":
        // Learn the conversation from the first incoming message if we don't
        // have one yet (a participant just started chatting).
        setChatId((current) => current ?? event.chat_id);
        setMessages((prev) => [...prev, normalize(event)]);
        break;
      case "receipt":
        setMessages((prev) =>
          prev.map((m) =>
            m.id === event.message_id ? { ...m, status: event.status } : m
          )
        );
        break;
      case "reset":
        // Server cleared all conversations — drop back to the no-chat state.
        setChatId(null);
        setMessages([]);
        break;
      default:
        console.warn("Unhandled WebSocket event type:", event.type);
    }
  }, []);

  const connectionStatus = useWebSocket(WS_URL, handleEvent, !USE_MOCK);

  const send = useCallback(
    async (text) => {
      if (chatId == null) return; // composer is disabled; guard anyway
      const id = crypto.randomUUID();
      const optimistic = {
        id,
        chat_id: chatId,
        text,
        timestamp: new Date().toISOString(),
        sender: "agent", // the agent speaks as the bot
        status: "pending",
      };
      setMessages((prev) => [...prev, optimistic]);

      // Mock mode: no backend. Mark the message sent, then echo a participant
      // reply so both bubble styles and the optimistic flow are visible.
      if (USE_MOCK) {
        setTimeout(() => updateStatus(setMessages, id, "sent"), 300);
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              chat_id: chatId,
              text: `Echo: ${text}`,
              timestamp: new Date().toISOString(),
              sender: "user",
              status: "received",
            },
          ]);
        }, 1200);
        return;
      }

      try {
        const saved = await sendMessage(optimistic);
        if (saved?.status) {
          updateStatus(setMessages, id, saved.status);
        }
      } catch (err) {
        console.error("Send failed", err);
        updateStatus(setMessages, id, "failed");
      }
    },
    [chatId]
  );

  const reset = useCallback(async () => {
    // Clear local state immediately; the server broadcast also resets any other
    // connected tabs. In mock mode there's no backend to call.
    if (!USE_MOCK) {
      try {
        await resetChat();
      } catch (err) {
        console.error("Reset failed", err);
      }
    }
    setChatId(null);
    setMessages([]);
  }, []);

  return { messages, connectionStatus, send, canSend: chatId != null, reset };
}

// Set the delivery status of the message identified by id.
function updateStatus(setMessages, id, status) {
  setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status } : m)));
}

// Normalize a server message into the client's shape.
function normalize(msg) {
  return {
    id: msg.id,
    chat_id: msg.chat_id,
    text: msg.text,
    timestamp: msg.timestamp,
    sender: msg.sender,
    status: msg.status,
  };
}
