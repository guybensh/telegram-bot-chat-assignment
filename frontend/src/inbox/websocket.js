import { upsertConversationList } from "./conversations";
import { threadKey } from "./keys";
import { appendToThread, updateMessageStatus } from "./messages";
import { bumpUnread } from "./unread";
import { emptyInboxState } from "./state";

export function applyWebSocketEvent(state, event, { botUsername, chatId }) {
  switch (event.type) {
    case "message": {
      const msgBot = event.bot_username;
      if (!msgBot) return { state, reloadBots: true };

      const isSelectedBot = botUsername === msgBot;
      const unread = bumpUnread(state, {
        msgBot,
        chatId: event.chat_id,
        botUsername,
        routeChatId: chatId,
      });

      const key = threadKey(msgBot, event.chat_id);
      let next = {
        ...state,
        unreadByChatId: unread.unreadByChatId,
        unreadByBotUsername: unread.unreadByBotUsername,
        messagesByThread: appendToThread(state.messagesByThread, key, event),
      };

      // Update the visible conversation list when home or viewing this bot.
      if (!botUsername || isSelectedBot) {
        next = {
          ...next,
          conversations: upsertConversationList(
            next.conversations,
            msgBot,
            event
          ),
        };
      }

      return { state: next, reloadBots: true };
    }
    case "receipt": {
      if (!event.bot_username) return { state };
      const key = threadKey(event.bot_username, event.chat_id);
      return {
        state: {
          ...state,
          messagesByThread: updateMessageStatus(
            state.messagesByThread,
            key,
            event.message_id,
            event.status
          ),
        },
      };
    }
    case "reset":
      return { state: emptyInboxState(), reloadBots: true };
    default:
      console.warn("Unhandled WebSocket event type:", event.type);
      return { state };
  }
}
