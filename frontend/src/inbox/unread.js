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

  const unreadByBotUsername = msgBot
    ? {
        ...state.unreadByBotUsername,
        [msgBot]: (state.unreadByBotUsername[msgBot] || 0) + 1,
      }
    : state.unreadByBotUsername;

  return { unreadByChatId, unreadByBotUsername };
}

/** Clear thread unread and reduce the bot-level count by the same amount. */
export function clearUnreadForThread(
  unreadByChatId,
  unreadByBotUsername,
  botUsername,
  chatId
) {
  const key = threadKey(botUsername, chatId);
  const threadUnread = unreadByChatId[key] || 0;
  const botUnread = unreadByBotUsername[botUsername] || 0;

  return {
    unreadByChatId: {
      ...unreadByChatId,
      [key]: 0,
    },
    unreadByBotUsername: {
      ...unreadByBotUsername,
      [botUsername]: Math.max(0, botUnread - threadUnread),
    },
  };
}
