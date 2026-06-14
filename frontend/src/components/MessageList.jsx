import { useEffect, useRef } from "react";
import { Message } from "./Message";

const keyOf = (m) => m.id;

export function MessageList({ messages }) {
  const containerRef = useRef(null);

  // Keep the latest message in view within the messages panel only.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat-messages" ref={containerRef}>
      {messages.length === 0 && (
        <p className="chat-empty">No messages in this conversation yet.</p>
      )}
      {messages.map((message) => (
        <Message key={keyOf(message)} message={message} />
      ))}
    </div>
  );
}
