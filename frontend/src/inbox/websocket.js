import { upsertConversationList } from "./conversations";
import { threadKey } from "./keys";
import { appendToThread, updateMessageStatus } from "./messages";
import { emptyInboxState } from "./state";

function upsertConversationsForBot(state, botUsername, event) {
  const existing = state.conversationsByBot[botUsername] || [];
  return {
    ...state.conversationsByBot,
    [botUsername]: upsertConversationList(existing, botUsername, event),
  };
}

export function applyWebSocketEvent(state, event, { botUsername, chatId }) {
  switch (event.type) {
    case "message": {
      const msgBot = event.bot_username;
      if (!msgBot) return { state, reloadBots: true };

      const key = threadKey(msgBot, event.chat_id);
      const next = {
        ...state,
        messagesByThread: appendToThread(state.messagesByThread, key, event),
        conversationsByBot: upsertConversationsForBot(state, msgBot, event),
      };

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
