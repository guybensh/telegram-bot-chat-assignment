import { threadKey } from "./keys";

export function bumpUnread(state, { msgBot, chatId, botUsername, routeChatId }) {
  const isViewingThread = botUsername === msgBot && routeChatId === chatId;
  if (isViewingThread) {
    return {
      unreadByChatId: state.unreadByChatId,
      unreadByBotUsername: state.unreadByBotUsername,
    };
  }

  const key = msgBot ? threadKey(msgBot, chatId) : String(chatId);
  const unreadByChatId = {
    ...state.unreadByChatId,
    [key]: (state.unreadByChatId[key] || 0) + 1,
  };

  const isSelectedBot = botUsername === msgBot;
  const unreadByBotUsername =
    !isSelectedBot && msgBot
      ? {
          ...state.unreadByBotUsername,
          [msgBot]: (state.unreadByBotUsername[msgBot] || 0) + 1,
        }
      : state.unreadByBotUsername;

  return { unreadByChatId, unreadByBotUsername };
}

export function clearUnreadForChat(unreadByChatId, botUsername, chatId) {
  return {
    ...unreadByChatId,
    [threadKey(botUsername, chatId)]: 0,
  };
}

export function clearUnreadForBot(unreadByBotUsername, botUsername) {
  return { ...unreadByBotUsername, [botUsername]: 0 };
}
