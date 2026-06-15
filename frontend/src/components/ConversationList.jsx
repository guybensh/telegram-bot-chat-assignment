import { formatConversationTime } from "../utils/time";

function previewText(conversation) {
  if (!conversation.last_message_text) {
    return "Waiting for first message…";
  }
  const prefix = conversation.last_sender === "agent" ? "You: " : "";
  return `${prefix}${conversation.last_message_text}`;
}

export function ConversationList({
  botUsername,
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
        {!botUsername && (
          <li className="inbox-empty">Select a bot to view conversations.</li>
        )}
        {botUsername && conversations.length === 0 && (
          <li className="inbox-empty">
            No active conversations yet. When a Telegram user messages the bot,
            the thread will appear here.
          </li>
        )}
        {conversations.map((conversation) => {
          const active = conversation.chat_id === selectedChatId;
          const unread =
            unreadByChatId[`${botUsername}:${conversation.chat_id}`] || 0;
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
                    {formatConversationTime(conversation.last_message_at)}
                  </span>
                </div>
                <div className="inbox-list-item-row">
                  <span className="inbox-list-item-preview">
                    {previewText(conversation)}
                  </span>
                  <span className="inbox-list-item-trailing">
                    {unread > 0 && (
                      <span className="inbox-unread-badge">{unread}</span>
                    )}
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
