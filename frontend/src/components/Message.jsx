// Renders a single chat bubble. Only "user" (the remote Telegram user) is
// incoming; everything from our side — "agent" (the human) and the reserved
// "bot" (future automated replies) — is outgoing. Mapped to the existing CSS
// classes; delivery ticks show only on our own messages.
const STATUS_LABEL = {
  pending: "🕓",
  sent: "✓",
  failed: "⚠ failed",
};

function formatTime(timestamp) {
  if (!timestamp) return "";
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function Message({ message }) {
  const isOutgoing = message.sender !== "user";
  return (
    <div className={`chat-message ${isOutgoing ? "outgoing" : "incoming"}`}>
      <div className="chat-bubble">
        <div className="chat-text">{message.text}</div>
        <div className="chat-meta">
          <span className="chat-timestamp">{formatTime(message.timestamp)}</span>
          {isOutgoing && message.status && (
            <span className={`chat-status ${message.status}`}>
              {STATUS_LABEL[message.status] ?? ""}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
