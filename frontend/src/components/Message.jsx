// Renders a single chat bubble. Only "user" (the remote Telegram user) is
// incoming; everything from our side — "agent" (the human) and the reserved
// "bot" (future automated replies) — is outgoing. Mapped to the existing CSS
// classes; delivery ticks show only on our own messages.
import { formatMessageTime } from "../utils/time";
const STATUS_LABEL = {
  pending: "🕓",
  sent: "✓",
  failed: "⚠ failed",
};

const SENDER_LABEL = {
  user: "user",
  agent: "agent",
  bot: "bot",
};

export function Message({ message }) {
  const isOutgoing = message.sender !== "user";
  const senderLabel = SENDER_LABEL[message.sender] ?? message.sender;

  return (
    <div className={`chat-message ${isOutgoing ? "outgoing" : "incoming"}`}>
      {!isOutgoing && (
        <span className="chat-sender-label">{senderLabel}</span>
      )}
      <div className="chat-bubble">
        <div className="chat-text">{message.text}</div>
        <div className="chat-meta">
          <span className="chat-timestamp">{formatMessageTime(message.timestamp)}</span>
          {isOutgoing && message.status && (
            <span className={`chat-status ${message.status}`}>
              {STATUS_LABEL[message.status] ?? ""}
            </span>
          )}
        </div>
      </div>
      {isOutgoing && (
        <span className="chat-sender-label">{senderLabel}</span>
      )}
    </div>
  );
}
