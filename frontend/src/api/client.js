import { API_URL } from "../config";

// Thin REST layer. The client never talks to Telegram directly — it only knows
// about these two endpoints. Server-initiated events arrive over the WebSocket
// (see hooks/useWebSocket.js), keeping a clean request/response vs. push split.

/**
 * Load the message history for the current session.
 * Returns an array of messages in server-defined order.
 */
export async function fetchHistory() {
  const res = await fetch(`${API_URL}/messages`);
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
