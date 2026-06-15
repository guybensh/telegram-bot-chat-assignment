import { threadKey } from "./keys";

export function selectMessages(state, botUsername, chatId) {
  if (botUsername == null || chatId == null) return [];
  return state.messagesByThread[threadKey(botUsername, chatId)] || [];
}

export function selectConversations(state, botUsername) {
  if (!botUsername) return [];
  return state.conversationsByBot[botUsername] || [];
}

export function selectConversation(state, botUsername, chatId) {
  if (chatId == null) return null;
  return (
    selectConversations(state, botUsername).find((c) => c.chat_id === chatId) ?? {
      chat_id: chatId,
      bot_username: botUsername,
      title: `Chat ${chatId}`,
    }
  );
}
