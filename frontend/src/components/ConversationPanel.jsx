import { ChatHeader } from "./ChatHeader";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";

export function ConversationPanel({
  conversation,
  messages,
  connectionStatus,
  canSend,
  onSend,
  onReset,
}) {
  if (!conversation) {
    return (
      <section className="inbox-panel inbox-panel--thread inbox-thread-empty">
        <p>Select a conversation to view messages</p>
      </section>
    );
  }

  return (
    <section className="inbox-panel inbox-panel--thread">
      <ChatHeader
        title={conversation.title}
        connectionStatus={connectionStatus}
        onReset={onReset}
      />
      <MessageList messages={messages} />
      <MessageInput onSend={onSend} disabled={!canSend} />
    </section>
  );
}
