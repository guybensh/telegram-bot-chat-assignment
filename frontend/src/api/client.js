import { API_URL } from "../config";

/**
 * List configured Telegram bots for the inbox sidebar.
 */
export async function fetchBots() {
  const res = await fetch(`${API_URL}/bots`);
  if (!res.ok) {
    throw new Error(`Failed to load bots (${res.status})`);
  }
  return res.json();
}

/**
 * List active chat summaries for one bot (inbox preview rows).
 */
export async function fetchChatSummaries(botUsername) {
  const res = await fetch(
    `${API_URL}/bots/${encodeURIComponent(botUsername)}/chat-summaries`
  );
  if (!res.ok) {
    throw new Error(`Failed to load chat summaries (${res.status})`);
  }
  return res.json();
}

/**
 * Admin/dev: clear all conversation state on the server.
 */
export async function resetChat() {
  const res = await fetch(`${API_URL}/reset`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Reset failed (${res.status})`);
  }
  return res.json();
}

/**
 * Load one conversation's message history, in server-defined order.
 */
export async function fetchMessages(botUsername, chatId) {
  const res = await fetch(
    `${API_URL}/bots/${encodeURIComponent(botUsername)}/chats/${encodeURIComponent(chatId)}/messages`
  );
  if (!res.ok) {
    throw new Error(`Failed to load history (${res.status})`);
  }
  return res.json();
}

/**
 * Mark user messages in a thread as read up to `read_at`.
 */
export async function markMessagesRead(botUsername, chatId, readAt) {
  const res = await fetch(
    `${API_URL}/bots/${encodeURIComponent(botUsername)}/chats/${encodeURIComponent(chatId)}/messages/read`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ read_at: readAt }),
    }
  );
  if (!res.ok) {
    throw new Error(`Mark read failed (${res.status})`);
  }
  return res.json();
}

/**
 * Forward an outgoing message to the connected Telegram chat.
 */
export async function sendMessage(botUsername, chatId, { id, text, timestamp }) {
  const res = await fetch(
    `${API_URL}/bots/${encodeURIComponent(botUsername)}/chats/${encodeURIComponent(chatId)}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, text, timestamp }),
    }
  );
  if (!res.ok) {
    throw new Error(`Send failed (${res.status})`);
  }
  return res.json();
}
