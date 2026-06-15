export function threadKey(botUsername, chatId) {
  return `${botUsername}:${chatId}`;
}
