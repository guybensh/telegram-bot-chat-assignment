export function normalizeMessage(msg) {
  return {
    id: msg.id,
    bot_id: String(msg.bot_id),
    chat_id: String(msg.chat_id),
    text: msg.text,
    timestamp: msg.timestamp,
    sender: msg.sender,
    status: msg.status,
    read_at: msg.read_at ?? null,
  };
}

export function conversationFromMessage(botUsername, event) {
  return {
    chat_id: event.chat_id,
    bot_id: event.bot_id,
    bot_username: botUsername,
    title: `Chat ${event.chat_id}`,
    last_message_text: event.text,
    last_message_at: event.timestamp,
    last_sender: event.sender,
  };
}
