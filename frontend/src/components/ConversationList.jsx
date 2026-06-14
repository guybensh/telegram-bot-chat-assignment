function formatTime(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();
  if (sameDay) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function previewText(conversation) {
  if (!conversation.last_message_text) {
    return "Waiting for first message…";
  }
  const prefix = conversation.last_sender === "agent" ? "You: " : "";
  return `${prefix}${conversation.last_message_text}`;
}

export function ConversationList({
  conversations,
  selectedChatId,
  unreadByChatId,
  onSelect,
}) {
  return (
    <aside className="inbox-panel inbox-panel--conversations">
      <div className="inbox-panel-header">
        <h2>Conversations</h2>
      </div>
      <ul className="inbox-list">
        {conversations.length === 0 && (
          <li className="inbox-empty">
            No active conversations yet. When a Telegram user messages the bot,
            the thread will appear here.
          </li>
        )}
        {conversations.map((conversation) => {
          const active = conversation.chat_id === selectedChatId;
          const unread = unreadByChatId[conversation.chat_id] || 0;
          return (
            <li key={conversation.chat_id}>
              <button
                type="button"
                className={`inbox-list-item${active ? " active" : ""}`}
                onClick={() => onSelect(conversation.chat_id)}
              >
                <div className="inbox-list-item-row">
                  <span className="inbox-list-item-title">
                    {conversation.title}
                  </span>
                  <span className="inbox-list-item-time">
                    {formatTime(conversation.last_message_at)}
                  </span>
                </div>
                <div className="inbox-list-item-row">
                  <span className="inbox-list-item-preview">
                    {previewText(conversation)}
                  </span>
                  {unread > 0 && (
                    <span className="inbox-unread-badge">{unread}</span>
                  )}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
