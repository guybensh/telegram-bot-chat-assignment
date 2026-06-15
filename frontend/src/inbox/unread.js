import { parseThreadKey, threadKey } from "./keys";

/** User messages without `read_at` count as unread. */
export function isUnreadMessage(message) {
  return message.sender === "user" && message.read_at == null;
}

export function countUnreadMessages(messages) {
  if (!messages?.length) return 0;
  return messages.filter(isUnreadMessage).length;
}

export function selectUnreadByChatId(state) {
  const unreadByChatId = {};
  for (const [key, messages] of Object.entries(state.messagesByThread)) {
    const count = countUnreadMessages(messages);
    if (count > 0) unreadByChatId[key] = count;
  }
  return unreadByChatId;
}

export function selectUnreadByBotUsername(state) {
  const unreadByBotUsername = {};
  for (const [key, messages] of Object.entries(state.messagesByThread)) {
    const parsed = parseThreadKey(key);
    if (!parsed) continue;
    const count = countUnreadMessages(messages);
    if (count > 0) {
      unreadByBotUsername[parsed.botUsername] =
        (unreadByBotUsername[parsed.botUsername] || 0) + count;
    }
  }
  return unreadByBotUsername;
}

export function markThreadReadInMessages(messagesByThread, botUsername, chatId, readAt) {
  const key = threadKey(botUsername, chatId);
  const thread = messagesByThread[key];
  if (!thread) return messagesByThread;

  const readAtMs = Date.parse(readAt);
  return {
    ...messagesByThread,
    [key]: thread.map((message) => {
      if (message.sender !== "user" || message.read_at != null) return message;
      if (Date.parse(message.timestamp) > readAtMs) return message;
      return { ...message, read_at: readAt };
    }),
  };
}
