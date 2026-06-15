import { mergeConversationLists, upsertConversationList } from "./conversations";
import { threadKey } from "./keys";
import { appendToThread, updateMessageStatus } from "./messages";
import { normalizeMessage } from "./normalize";
import { emptyInboxState } from "./state";
import { markThreadReadInMessages } from "./unread";
import { applyWebSocketEvent } from "./websocket";

export const inboxReducer = (state, action) => {
  switch (action.type) {
    case "BOTS_LOADED":
      return { ...state, bots: action.bots };

    case "CONVERSATIONS_LOADED": {
      const existing = state.conversationsByBot[action.botUsername] || [];
      return {
        ...state,
        conversationsByBot: {
          ...state.conversationsByBot,
          [action.botUsername]: mergeConversationLists(
            existing,
            action.conversations
          ),
        },
      };
    }

    case "SYNC_ACTIVE_CHATS":
      return {
        ...state,
        bots: state.bots.map((bot) =>
          bot.username === action.botUsername
            ? { ...bot, active_chats: action.count }
            : bot
        ),
      };

    case "THREAD_HISTORY_LOADED": {
      const { threadKey: key, history } = action;
      const existing = state.messagesByThread[key] || [];
      const normalized = history.map(normalizeMessage);
      const merged =
        existing.length === 0
          ? normalized
          : [
              ...normalized,
              ...existing.filter(
                (msg) => !normalized.some((item) => item.id === msg.id)
              ),
            ].sort(
              (a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp)
            );
      return {
        ...state,
        messagesByThread: {
          ...state.messagesByThread,
          [key]: merged,
        },
      };
    }

    case "WS_EVENT": {
      const { state: next } = applyWebSocketEvent(
        state,
        action.event,
        action.context
      );
      return next;
    }

    case "MARK_THREAD_READ": {
      const { botUsername, chatId, readAt } = action;
      return {
        ...state,
        messagesByThread: markThreadReadInMessages(
          state.messagesByThread,
          botUsername,
          chatId,
          readAt
        ),
      };
    }

    case "SEND_OPTIMISTIC": {
      const { optimistic, botUsername, chatId } = action;
      const key = threadKey(botUsername, chatId);
      return {
        ...state,
        messagesByThread: appendToThread(
          state.messagesByThread,
          key,
          optimistic
        ),
        conversationsByBot: {
          ...state.conversationsByBot,
          [botUsername]: upsertConversationList(
            state.conversationsByBot[botUsername] || [],
            botUsername,
            optimistic
          ),
        },
      };
    }

    case "MESSAGE_STATUS":
      return {
        ...state,
        messagesByThread: updateMessageStatus(
          state.messagesByThread,
          action.threadKey,
          action.messageId,
          action.status
        ),
      };

    case "RESET":
      return emptyInboxState();

    default:
      return state;
  }
};

export function shouldReloadBotsAfterWsEvent(event) {
  return event.type === "message" || event.type === "reset";
}
