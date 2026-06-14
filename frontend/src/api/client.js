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
 * List active conversations for one bot, with preview metadata for the inbox.
 */
export async function fetchBotConversations(botUsername) {
  const res = await fetch(
    `${API_URL}/bots/${encodeURIComponent(botUsername)}/conversations`
  );
  if (!res.ok) {
    throw new Error(`Failed to load conversations (${res.status})`);
  }
  return res.json();
}

/**
 * Admin/dev: clear all conversation state on the server.
 */
export async function resetChat() {
  const res = await fetch(`${API_URL}/admin/reset`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Reset failed (${res.status})`);
  }
  return res.json();
}

/**
 * Load one conversation's message history, in server-defined order.
 */
export async function fetchHistory(botUsername, chatId) {
  const res = await fetch(
    `${API_URL}/bots/${encodeURIComponent(botUsername)}/messages?chat_id=${chatId}`
  );
  if (!res.ok) {
    throw new Error(`Failed to load history (${res.status})`);
  }
  return res.json();
}

/**
 * Forward an outgoing message to the connected Telegram chat.
 */
export async function sendMessage(botUsername, message) {
  const res = await fetch(
    `${API_URL}/bots/${encodeURIComponent(botUsername)}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(message),
    }
  );
  if (!res.ok) {
    throw new Error(`Send failed (${res.status})`);
  }
  return res.json();
}
