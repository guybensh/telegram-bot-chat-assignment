// Renders a single chat bubble. The bubble side is driven by `sender` ("user" =
// our outgoing messages, "bot" = the incoming Telegram bot messages) and mapped
// to the existing CSS classes; delivery ticks show only on our own messages.
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
  const isOutgoing = message.sender === "user";
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
