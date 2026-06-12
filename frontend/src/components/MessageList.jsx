import { useEffect, useRef } from "react";
import { Message } from "./Message";

const keyOf = (m) => m.id;

export function MessageList({ messages }) {
  const bottomRef = useRef(null);

  // Keep the latest message in view as the conversation grows.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="chat-messages">
      {messages.length === 0 && (
        <p className="chat-empty">No messages yet. Say hello 👋</p>
      )}
      {messages.map((message) => (
        <Message key={keyOf(message)} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
