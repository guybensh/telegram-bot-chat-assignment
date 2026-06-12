import { API_URL } from "../config";

// Thin REST layer. The client never talks to Telegram directly — it only knows
// about these two endpoints. Server-initiated events arrive over the WebSocket
// (see hooks/useWebSocket.js), keeping a clean request/response vs. push split.

/**
 * List the active conversations so the client knows which chat exists and which
 * chat_id to reply to. Returns an array of `{ chat_id }`.
 */
export async function fetchConversations() {
  const res = await fetch(`${API_URL}/conversations`);
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
export async function fetchHistory(chatId) {
  const res = await fetch(`${API_URL}/messages?chat_id=${chatId}`);
  if (!res.ok) {
    throw new Error(`Failed to load history (${res.status})`);
  }
  return res.json();
}

/**
 * Forward an outgoing message to the connected Telegram chat. The client sends
 * the full message object (id, text, timestamp, sender, status) so the server
 * stores it verbatim — using the timestamp to order the conversation and the
 * sender/status as given — rather than reconstructing the record itself.
 * Returns the stored message; the client adopts any status the server reports.
 */
export async function sendMessage(message) {
  const res = await fetch(`${API_URL}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(message),
  });
  if (!res.ok) {
    throw new Error(`Send failed (${res.status})`);
  }
  return res.json();
}
