import { conversationFromMessage } from "./normalize";

export function sortConversations(list) {
  return [...list].sort((a, b) => {
    const aTime = a.last_message_at ? Date.parse(a.last_message_at) : 0;
    const bTime = b.last_message_at ? Date.parse(b.last_message_at) : 0;
    return bTime - aTime;
  });
}

export function upsertConversationList(conversations, botUsername, event) {
  if (!botUsername) return conversations;
  const row = conversationFromMessage(botUsername, event);
  const rest = conversations.filter((c) => c.chat_id !== event.chat_id);
  return sortConversations([row, ...rest]);
}

/** Keep WS-updated previews when a stale REST fetch completes later. */
export function mergeConversationLists(local, remote) {
  const byChatId = new Map();
  for (const conversation of remote) {
    byChatId.set(conversation.chat_id, conversation);
  }
  for (const conversation of local) {
    const existing = byChatId.get(conversation.chat_id);
    if (!existing) {
      byChatId.set(conversation.chat_id, conversation);
      continue;
    }
    const localTime = conversation.last_message_at
      ? Date.parse(conversation.last_message_at)
      : 0;
    const remoteTime = existing.last_message_at
      ? Date.parse(existing.last_message_at)
      : 0;
    if (localTime >= remoteTime) {
      byChatId.set(conversation.chat_id, conversation);
    }
  }
  return sortConversations([...byChatId.values()]);
}
