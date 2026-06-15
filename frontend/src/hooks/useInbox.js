import { useCallback, useEffect, useReducer } from "react";
import { USE_MOCK, WS_URL } from "../config";
import {
  fetchBotConversations,
  fetchBots,
  fetchHistory,
  resetChat,
  sendMessage,
} from "../api/client";
import { threadKey } from "../inbox/keys";
import { buildMockBots } from "../inbox/mock";
import {
  inboxReducer,
  shouldReloadBotsAfterWsEvent,
} from "../inbox/reducer";
import { selectConversation, selectConversations, selectMessages } from "../inbox/selectors";
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
    botUsername,
    createInitialInboxState
  );

  const loadBots = useCallback(() => {
    if (USE_MOCK) {
      dispatch({ type: "BOTS_LOADED", bots: buildMockBots() });
      return undefined;
    }
    let cancelled = false;
    fetchBots()
      .then((list) => {
        if (!cancelled) dispatch({ type: "BOTS_LOADED", bots: list });
      })
      .catch((err) => console.error("Could not load bots", err));
    return () => {
      cancelled = true;
    };
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
    },
    [botUsername, chatId, loadBots]
  );

  const connectionStatus = useWebSocket(WS_URL, handleEvent, !USE_MOCK);

  useEffect(() => loadBots(), [loadBots]);

  useEffect(() => {
    if (!botUsername) return;
    if (USE_MOCK) {
      dispatch({ type: "MOCK_SYNC_BOT", botUsername });
    }
  }, [botUsername]);

  useEffect(() => {
    if (!botUsername) return;
    dispatch({
      type: "SYNC_ACTIVE_CHATS",
      botUsername,
      count: selectConversations(state, botUsername).length,
    });
  }, [botUsername, state.conversationsByBot]);

  useEffect(() => {
    if (!botUsername || USE_MOCK) return undefined;
    let cancelled = false;
    fetchBotConversations(botUsername)
      .then((list) => {
        if (!cancelled) {
          dispatch({
            type: "CONVERSATIONS_LOADED",
            botUsername,
            conversations: list,
          });
        }
      })
      .catch((err) => console.error("Could not load conversations", err));
    return () => {
      cancelled = true;
    };
  }, [botUsername]);

  useEffect(() => {
    if (!botUsername || !chatId || USE_MOCK) return undefined;
    const key = threadKey(botUsername, chatId);

    let cancelled = false;
    fetchHistory(botUsername, chatId)
      .then((history) => {
        if (cancelled) return;
        dispatch({
          type: "THREAD_HISTORY_LOADED",
          threadKey: key,
          history,
        });
      })
      .catch((err) => console.error("Could not load history", err));
    return () => {
      cancelled = true;
    };
  }, [botUsername, chatId]);

  useEffect(() => {
    if (!botUsername || chatId == null) return;
    dispatch({ type: "CLEAR_UNREAD_THREAD", botUsername, chatId });
  }, [botUsername, chatId]);

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

      if (USE_MOCK) {
        setTimeout(
          () =>
            dispatch({
              type: "MESSAGE_STATUS",
              threadKey: key,
              messageId: id,
              status: "sent",
            }),
          300
        );
        setTimeout(() => {
          dispatch({
            type: "INCOMING_MESSAGE",
            botUsername,
            chatId,
            message: {
              id: crypto.randomUUID(),
              bot_id: optimistic.bot_id,
              chat_id: chatId,
              text: `Echo: ${text}`,
              timestamp: new Date().toISOString(),
              sender: "user",
              status: "received",
            },
          });
        }, 1200);
        return;
      }

      try {
        const saved = await sendMessage(botUsername, optimistic);
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
    if (!USE_MOCK) {
      try {
        await resetChat();
      } catch (err) {
        console.error("Reset failed", err);
      }
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
    unreadByChatId: state.unreadByChatId,
    unreadByBotUsername: state.unreadByBotUsername,
  };
}
