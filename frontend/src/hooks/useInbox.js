import { useCallback, useEffect, useReducer } from "react";
import { WS_URL } from "../config";
import {
  fetchBots,
  fetchMessages,
  markMessagesRead,
  resetChat,
  sendMessage,
} from "../api/client";
import { threadKey } from "../inbox/keys";
import { prefetchBotThreadHistories } from "../inbox/prefetch";
import {
  inboxReducer,
  shouldReloadBotsAfterWsEvent,
} from "../inbox/reducer";
import { selectConversation, selectConversations, selectMessages } from "../inbox/selectors";
import {
  selectUnreadByBotUsername,
  selectUnreadByChatId,
} from "../inbox/unread";
import { createInitialInboxState } from "../inbox/state";
import { useWebSocket } from "./useWebSocket";

/**
 * Inbox state for bots → conversations → messages.
 *
 * URL params (`botUsername`, `chatId`) select the active thread. WebSocket
 * events are filtered by `bot_username` and routed by `chat_id`.
 */
export function useInbox(botUsername, chatId) {
  const [state, dispatch] = useReducer(
    inboxReducer,
    undefined,
    createInitialInboxState
  );

  const loadBots = useCallback(() => {
    let cancelled = false;
    fetchBots()
      .then((list) => {
        if (cancelled) return;
        dispatch({ type: "BOTS_LOADED", bots: list });
        list.forEach((bot) => {
          prefetchBotThreadHistories(bot.username, dispatch).catch((err) =>
            console.error(`Could not prefetch threads for @${bot.username}`, err)
          );
        });
      })
      .catch((err) => console.error("Could not load bots", err));
    return () => {
      cancelled = true;
    };
  }, []);

  const markThreadRead = useCallback((targetBotUsername, targetChatId) => {
    const readAt = new Date().toISOString();
    dispatch({
      type: "MARK_THREAD_READ",
      botUsername: targetBotUsername,
      chatId: targetChatId,
      readAt,
    });
    markMessagesRead(targetBotUsername, targetChatId, readAt).catch((err) =>
      console.error("Mark read failed", err)
    );
  }, []);

  const handleEvent = useCallback(
    (event) => {
      dispatch({
        type: "WS_EVENT",
        event,
        context: { botUsername, chatId },
      });
      if (shouldReloadBotsAfterWsEvent(event)) {
        loadBots();
      }
      if (
        event.type === "message" &&
        event.bot_username === botUsername &&
        String(event.chat_id) === String(chatId)
      ) {
        markThreadRead(botUsername, chatId);
      }
    },
    [botUsername, chatId, loadBots, markThreadRead]
  );

  const connectionStatus = useWebSocket(WS_URL, handleEvent);

  useEffect(() => loadBots(), [loadBots]);

  useEffect(() => {
    if (!botUsername) return;
    dispatch({
      type: "SYNC_ACTIVE_CHATS",
      botUsername,
      count: selectConversations(state, botUsername).length,
    });
  }, [botUsername, state.conversationsByBot]);

  useEffect(() => {
    if (!botUsername) return;
    prefetchBotThreadHistories(botUsername, dispatch).catch((err) =>
      console.error("Could not load conversations", err)
    );
  }, [botUsername]);

  useEffect(() => {
    if (!botUsername || !chatId) return undefined;

    const key = threadKey(botUsername, chatId);
    let cancelled = false;
    fetchMessages(botUsername, chatId)
      .then((history) => {
        if (cancelled) return;
        dispatch({
          type: "THREAD_HISTORY_LOADED",
          threadKey: key,
          history,
        });
        if (history.length) {
          markThreadRead(botUsername, chatId);
        }
      })
      .catch((err) => console.error("Could not load history", err));
    return () => {
      cancelled = true;
    };
  }, [botUsername, chatId, markThreadRead]);

  const send = useCallback(
    async (text) => {
      if (chatId == null || !botUsername) return;
      const id = crypto.randomUUID();
      const optimistic = {
        id,
        bot_id: state.bots.find((b) => b.username === botUsername)?.bot_id,
        chat_id: chatId,
        text,
        timestamp: new Date().toISOString(),
        sender: "agent",
        status: "pending",
      };
      const key = threadKey(botUsername, chatId);

      dispatch({ type: "SEND_OPTIMISTIC", optimistic, botUsername, chatId });

      try {
        const saved = await sendMessage(botUsername, chatId, {
          id,
          text,
          timestamp: optimistic.timestamp,
        });
        if (saved?.status) {
          dispatch({
            type: "MESSAGE_STATUS",
            threadKey: key,
            messageId: id,
            status: saved.status,
          });
        }
      } catch (err) {
        console.error("Send failed", err);
        dispatch({
          type: "MESSAGE_STATUS",
          threadKey: key,
          messageId: id,
          status: "failed",
        });
      }
    },
    [botUsername, chatId, state.bots]
  );

  const reset = useCallback(async () => {
    try {
      await resetChat();
    } catch (err) {
      console.error("Reset failed", err);
    }
    dispatch({ type: "RESET" });
    loadBots();
  }, [loadBots]);

  return {
    bots: state.bots,
    conversations: selectConversations(state, botUsername),
    selectedConversation: selectConversation(state, botUsername, chatId),
    messages: selectMessages(state, botUsername, chatId),
    connectionStatus,
    send,
    canSend: chatId != null,
    reset,
    unreadByChatId: selectUnreadByChatId(state),
    unreadByBotUsername: selectUnreadByBotUsername(state),
  };
}
