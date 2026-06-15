import { mergeConversationLists, upsertConversationList } from "./conversations";
import { threadKey } from "./keys";
import {
  buildMockBots,
  mockConversationsForBot,
} from "./mock";
import { appendToThread, updateMessageStatus } from "./messages";
import { normalizeMessage } from "./normalize";
import { emptyInboxState } from "./state";
import {
  clearUnreadForBot,
  clearUnreadForChat,
} from "./unread";
import { applyWebSocketEvent } from "./websocket";

export const inboxReducer = (state, action) => {
  switch (action.type) {
    case "BOTS_LOADED":
      return { ...state, bots: action.bots };

    case "CONVERSATIONS_LOADED":
      return {
        ...state,
        conversations: mergeConversationLists(
          state.conversations,
          action.conversations
        ),
      };

    case "CONVERSATIONS_CLEARED":
      return { ...state, conversations: [] };

    case "MOCK_SYNC_BOT":
      return {
        ...state,
        bots: buildMockBots(),
        conversations: mockConversationsForBot(action.botUsername),
      };

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
      // Keep WS messages that arrived before history finished loading.
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

    case "CLEAR_UNREAD_CHAT":
      return {
        ...state,
        unreadByChatId: clearUnreadForChat(
          state.unreadByChatId,
          action.botUsername,
          action.chatId
        ),
      };

    case "CLEAR_UNREAD_BOT":
      return {
        ...state,
        unreadByBotUsername: clearUnreadForBot(
          state.unreadByBotUsername,
          action.botUsername
        ),
      };

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
        conversations: upsertConversationList(
          state.conversations,
          botUsername,
          optimistic
        ),
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

    case "INCOMING_MESSAGE": {
      const { message, botUsername, chatId } = action;
      const key = threadKey(botUsername, chatId);
      return {
        ...state,
        messagesByThread: appendToThread(state.messagesByThread, key, message),
        conversations: upsertConversationList(
          state.conversations,
          botUsername,
          message
        ),
      };
    }

    case "RESET":
      return emptyInboxState();

    default:
      return state;
  }
};

export function shouldReloadBotsAfterWsEvent(event) {
  return event.type === "message" || event.type === "reset";
}
