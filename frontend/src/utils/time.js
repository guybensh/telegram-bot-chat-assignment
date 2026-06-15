/** Time-only label for a message bubble (e.g. "14:32"). */
export function formatMessageTime(timestamp) {
  if (!timestamp) return "";
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Inbox list label: time today, short date otherwise (e.g. "Jun 14"). */
export function formatConversationTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  if (sameDay) {
    return formatMessageTime(iso);
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}
