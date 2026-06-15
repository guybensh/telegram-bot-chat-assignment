import { threadKey } from "./keys";

export function selectMessages(state, botUsername, chatId) {
  if (botUsername == null || chatId == null) return [];
  return state.messagesByThread[threadKey(botUsername, chatId)] || [];
}

export function selectConversation(state, botUsername, chatId) {
  if (chatId == null) return null;
  return (
    state.conversations.find((c) => c.chat_id === chatId) ?? {
      chat_id: chatId,
      bot_username: botUsername,
      title: `Chat ${chatId}`,
    }
  );
}
