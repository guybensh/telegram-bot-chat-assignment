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

function scopedKey(botUsername, chatId) {
  return `${botUsername}:${chatId}`;
}

function updateStatusForThread(
  setMessagesByThread,
  threadKey,
  messageId,
  status
) {
  setMessagesByThread((prev) => {
    const thread = prev[threadKey];
    if (!thread) return prev;
    return {
      ...prev,
      [threadKey]: thread.map((m) =>
        m.id === messageId ? { ...m, status } : m
      ),
    };
  });
}

function buildMockBots() {
  return mockBots.map((bot) => ({
    ...bot,
    active_chats: mockConversations.filter(
      (conversation) => conversation.bot_username === bot.username
    ).length,
  }));
}

function buildMockMessagesByThread() {
  const out = {};
  for (const conversation of mockConversations) {
    const messages = seedMessagesByChat[conversation.chat_id];
    if (messages) {
      out[scopedKey(conversation.bot_username, conversation.chat_id)] = messages;
    }
  }
  return out;
}

/**
 * Inbox state for bots → conversations → messages.
 *
 * URL params (`botUsername`, `chatId`) select the active thread. WebSocket
 * events are filtered by `bot_username` and routed by `chat_id`.
 */
export function useInbox(botUsername, chatId) {
  const [bots, setBots] = useState(USE_MOCK ? buildMockBots() : []);
  const [conversations, setConversations] = useState(
    USE_MOCK ? mockConversations.filter((c) => c.bot_username === botUsername) : []
  );
  const [messagesByThread, setMessagesByThread] = useState(
    USE_MOCK ? buildMockMessagesByThread() : {}
  );
  const [unreadByChatId, setUnreadByChatId] = useState({});
  const [unreadByBotUsername, setUnreadByBotUsername] = useState({});

  const loadBots = useCallback(() => {
    if (USE_MOCK) {
      setBots(buildMockBots());
      return undefined;
    }
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
      switch (event.type) {
        case "message": {
          const msgBot = event.bot_username;
          const isViewingThread =
            botUsername === msgBot && chatId === event.chat_id;
          const isSelectedBot = botUsername === msgBot;

          if (!isViewingThread) {
            const key = msgBot
              ? scopedKey(msgBot, event.chat_id)
              : String(event.chat_id);
            setUnreadByChatId((prev) => ({
              ...prev,
              [key]: (prev[key] || 0) + 1,
            }));
            if (!isSelectedBot && msgBot) {
              setUnreadByBotUsername((prev) => ({
                ...prev,
                [msgBot]: (prev[msgBot] || 0) + 1,
              }));
            }
          }

          if ((!botUsername || isSelectedBot) && msgBot) {
            const key = scopedKey(msgBot, event.chat_id);
            setMessagesByThread((prev) => ({
              ...prev,
              [key]: [...(prev[key] || []), normalize(event)],
            }));
            upsertConversation(event);
          }
          loadBots();
          break;
        }
        case "receipt":
          if (event.bot_username) {
            updateStatusForThread(
              setMessagesByThread,
              scopedKey(event.bot_username, event.chat_id),
              event.message_id,
              event.status
            );
          }
          break;
        case "reset":
          setConversations([]);
          setMessagesByThread({});
          setUnreadByChatId({});
          setUnreadByBotUsername({});
          loadBots();
          break;
        default:
          console.warn("Unhandled WebSocket event type:", event.type);
      }
    },
    [botUsername, chatId, upsertConversation, loadBots]
  );

  const connectionStatus = useWebSocket(WS_URL, handleEvent, !USE_MOCK);

  useEffect(() => loadBots(), [loadBots]);

  useEffect(() => {
    if (!botUsername) {
      setConversations([]);
      return;
    }
    if (!USE_MOCK) return;
    setConversations(
      mockConversations.filter((c) => c.bot_username === botUsername)
    );
    setBots(buildMockBots());
  }, [botUsername]);

  useEffect(() => {
    if (!botUsername) return;
    setBots((prev) =>
      prev.map((bot) =>
        bot.username === botUsername
          ? { ...bot, active_chats: conversations.length }
          : bot
      )
    );
  }, [botUsername, conversations.length]);

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
    const key = scopedKey(botUsername, chatId);
    if (messagesByThread[key]) return undefined;

    let cancelled = false;
    fetchHistory(botUsername, chatId)
      .then((history) => {
        if (cancelled) return;
        setMessagesByThread((prev) => ({
          ...prev,
          [key]: history.map(normalize),
        }));
      })
      .catch((err) => console.error("Could not load history", err));
    return () => {
      cancelled = true;
    };
  }, [botUsername, chatId, messagesByThread]);

  useEffect(() => {
    if (!botUsername || chatId == null) return;
    setUnreadByChatId((prev) => ({
      ...prev,
      [scopedKey(botUsername, chatId)]: 0,
    }));
  }, [botUsername, chatId]);

  useEffect(() => {
    if (!botUsername) return;
    setUnreadByBotUsername((prev) => ({ ...prev, [botUsername]: 0 }));
  }, [botUsername]);

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

      setMessagesByThread((prev) => ({
        ...prev,
        [scopedKey(botUsername, chatId)]: [
          ...(prev[scopedKey(botUsername, chatId)] || []),
          optimistic,
        ],
      }));
      upsertConversation(optimistic);

      if (USE_MOCK) {
        setTimeout(
          () =>
            updateStatusForThread(
              setMessagesByThread,
              scopedKey(botUsername, chatId),
              id,
              "sent"
            ),
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
          setMessagesByThread((prev) => ({
            ...prev,
            [scopedKey(botUsername, chatId)]: [
              ...(prev[scopedKey(botUsername, chatId)] || []),
              reply,
            ],
          }));
          upsertConversation(reply);
        }, 1200);
        return;
      }

      try {
        const saved = await sendMessage(botUsername, optimistic);
        if (saved?.status) {
          updateStatusForThread(
            setMessagesByThread,
            scopedKey(botUsername, chatId),
            id,
            saved.status
          );
        }
      } catch (err) {
        console.error("Send failed", err);
        updateStatusForThread(
          setMessagesByThread,
          scopedKey(botUsername, chatId),
          id,
          "failed"
        );
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
    setMessagesByThread({});
    setUnreadByChatId({});
    setUnreadByBotUsername({});
    loadBots();
  }, [loadBots]);

  const selectedConversation =
    conversations.find((c) => c.chat_id === chatId) ??
    (chatId != null
      ? {
          chat_id: chatId,
          bot_username: botUsername,
          title: `Chat ${chatId}`,
        }
      : null);
  const messages =
    botUsername != null && chatId != null
      ? messagesByThread[scopedKey(botUsername, chatId)] || []
      : [];

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
    unreadByBotUsername,
  };
}
