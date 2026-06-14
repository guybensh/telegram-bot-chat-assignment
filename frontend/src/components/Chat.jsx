import { ChatHeader } from "./ChatHeader";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";

export function Chat({ botUsername, conversation, messages, canSend, onSend }) {
  if (!botUsername) {
    return (
      <section className="inbox-panel inbox-panel--thread">
        <ChatHeader title="Messages" />
        <div className="inbox-thread-empty">
          <p>Select a bot to get started</p>
        </div>
      </section>
    );
  }

  return (
    <section className="inbox-panel inbox-panel--thread">
      <ChatHeader title={conversation?.title ?? "Messages"} />
      {!conversation ? (
        <div className="inbox-thread-empty">
          <p>Select a conversation to view messages</p>
        </div>
      ) : (
        <>
          <MessageList messages={messages} />
          <MessageInput onSend={onSend} disabled={!canSend} />
        </>
      )}
    </section>
  );
}
