import { useCallback, useEffect, useState } from "react";
import { USE_MOCK, WS_URL } from "../config";
import {
  fetchBotConversations,
  fetchBots,
  fetchHistory,
  resetChat,
  sendMessage,
} from "../api/client";
import { useWebSocket } from "./useWebSocket";
import {
  mockBots,
  mockConversations,
  seedMessagesByChat,
} from "../../__mocks__/seedMessages";

function normalize(msg) {
  return {
    id: msg.id,
    bot_id: msg.bot_id,
    chat_id: msg.chat_id,
    text: msg.text,
    timestamp: msg.timestamp,
    sender: msg.sender,
    status: msg.status,
  };
}

function sortConversations(list) {
  return [...list].sort((a, b) => {
    const aTime = a.last_message_at ? Date.parse(a.last_message_at) : 0;
    const bTime = b.last_message_at ? Date.parse(b.last_message_at) : 0;
    return bTime - aTime;
  });
}

function conversationFromMessage(botUsername, event) {
  return {
    chat_id: event.chat_id,
    bot_id: event.bot_id,
    bot_username: botUsername,
    title: `Chat ${event.chat_id}`,
    last_message_text: event.text,
    last_message_at: event.timestamp,
    last_sender: event.sender,
  };
}

function updateStatusForChat(setMessagesByChatId, chatId, messageId, status) {
  setMessagesByChatId((prev) => {
    const thread = prev[chatId];
    if (!thread) return prev;
    return {
      ...prev,
      [chatId]: thread.map((m) =>
        m.id === messageId ? { ...m, status } : m
      ),
    };
  });
}

/**
 * Inbox state for bots → conversations → messages.
 *
 * URL params (`botUsername`, `chatId`) select the active thread. WebSocket
 * events are filtered by `bot_username` and routed by `chat_id`.
 */
export function useInbox(botUsername, chatId) {
  const [bots, setBots] = useState(USE_MOCK ? mockBots : []);
  const [conversations, setConversations] = useState(
    USE_MOCK ? mockConversations.filter((c) => c.bot_username === botUsername) : []
  );
  const [messagesByChatId, setMessagesByChatId] = useState(
    USE_MOCK ? seedMessagesByChat : {}
  );
  const [unreadByChatId, setUnreadByChatId] = useState({});

  const upsertConversation = useCallback(
    (event) => {
      if (!botUsername) return;
      const row = conversationFromMessage(botUsername, event);
      setConversations((prev) => {
        const rest = prev.filter((c) => c.chat_id !== event.chat_id);
        return sortConversations([row, ...rest]);
      });
    },
    [botUsername]
  );

  const handleEvent = useCallback(
    (event) => {
      if (
        event.bot_username &&
        botUsername &&
        event.bot_username !== botUsername
      ) {
        return;
      }

      switch (event.type) {
        case "message": {
          const id = event.chat_id;
          setMessagesByChatId((prev) => ({
            ...prev,
            [id]: [...(prev[id] || []), normalize(event)],
          }));
          upsertConversation(event);
          if (id !== chatId) {
            setUnreadByChatId((prev) => ({
              ...prev,
              [id]: (prev[id] || 0) + 1,
            }));
          }
          break;
        }
        case "receipt":
          updateStatusForChat(
            setMessagesByChatId,
            event.chat_id,
            event.message_id,
            event.status
          );
          break;
        case "reset":
          setConversations([]);
          setMessagesByChatId({});
          setUnreadByChatId({});
          break;
        default:
          console.warn("Unhandled WebSocket event type:", event.type);
      }
    },
    [botUsername, chatId, upsertConversation]
  );

  const connectionStatus = useWebSocket(WS_URL, handleEvent, !USE_MOCK);

  useEffect(() => {
    if (!USE_MOCK || !botUsername) return;
    setConversations(
      mockConversations.filter((c) => c.bot_username === botUsername)
    );
  }, [botUsername]);

  useEffect(() => {
    if (USE_MOCK) return undefined;
    let cancelled = false;
    fetchBots()
      .then((list) => {
        if (!cancelled) setBots(list);
      })
      .catch((err) => console.error("Could not load bots", err));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!botUsername || USE_MOCK) return undefined;
    let cancelled = false;
    fetchBotConversations(botUsername)
      .then((list) => {
        if (!cancelled) setConversations(sortConversations(list));
      })
      .catch((err) => console.error("Could not load conversations", err));
    return () => {
      cancelled = true;
    };
  }, [botUsername]);

  useEffect(() => {
    if (!botUsername || !chatId || USE_MOCK) return undefined;
    if (messagesByChatId[chatId]) return undefined;

    let cancelled = false;
    fetchHistory(botUsername, chatId)
      .then((history) => {
        if (cancelled) return;
        setMessagesByChatId((prev) => ({
          ...prev,
          [chatId]: history.map(normalize),
        }));
      })
      .catch((err) => console.error("Could not load history", err));
    return () => {
      cancelled = true;
    };
  }, [botUsername, chatId, messagesByChatId]);

  useEffect(() => {
    if (!chatId) return;
    setUnreadByChatId((prev) => ({ ...prev, [chatId]: 0 }));
  }, [chatId]);

  const send = useCallback(
    async (text) => {
      if (chatId == null || !botUsername) return;
      const id = crypto.randomUUID();
      const optimistic = {
        id,
        bot_id: bots.find((b) => b.username === botUsername)?.bot_id,
        chat_id: chatId,
        text,
        timestamp: new Date().toISOString(),
        sender: "agent",
        status: "pending",
      };

      setMessagesByChatId((prev) => ({
        ...prev,
        [chatId]: [...(prev[chatId] || []), optimistic],
      }));
      upsertConversation(optimistic);

      if (USE_MOCK) {
        setTimeout(
          () => updateStatusForChat(setMessagesByChatId, chatId, id, "sent"),
          300
        );
        setTimeout(() => {
          const reply = {
            id: crypto.randomUUID(),
            bot_id: optimistic.bot_id,
            chat_id: chatId,
            text: `Echo: ${text}`,
            timestamp: new Date().toISOString(),
            sender: "user",
            status: "received",
          };
          setMessagesByChatId((prev) => ({
            ...prev,
            [chatId]: [...(prev[chatId] || []), reply],
          }));
          upsertConversation(reply);
        }, 1200);
        return;
      }

      try {
        const saved = await sendMessage(botUsername, optimistic);
        if (saved?.status) {
          updateStatusForChat(
            setMessagesByChatId,
            chatId,
            id,
            saved.status
          );
        }
      } catch (err) {
        console.error("Send failed", err);
        updateStatusForChat(setMessagesByChatId, chatId, id, "failed");
      }
    },
    [botUsername, bots, chatId, upsertConversation]
  );

  const reset = useCallback(async () => {
    if (!USE_MOCK) {
      try {
        await resetChat();
      } catch (err) {
        console.error("Reset failed", err);
      }
    }
    setConversations([]);
    setMessagesByChatId({});
    setUnreadByChatId({});
  }, []);

  const selectedConversation =
    conversations.find((c) => c.chat_id === chatId) ??
    (chatId != null
      ? {
          chat_id: chatId,
          bot_username: botUsername,
          title: `Chat ${chatId}`,
        }
      : null);
  const messages = chatId != null ? messagesByChatId[chatId] || [] : [];

  return {
    bots,
    conversations,
    selectedConversation,
    messages,
    connectionStatus,
    send,
    canSend: chatId != null,
    reset,
    unreadByChatId,
  };
}
