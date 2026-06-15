export function threadKey(botUsername, chatId) {
  return `${botUsername}:${chatId}`;
}

export function parseThreadKey(key) {
  const separator = key.indexOf(":");
  if (separator === -1) return null;
  return {
    botUsername: key.slice(0, separator),
    chatId: key.slice(separator + 1),
  };
}
