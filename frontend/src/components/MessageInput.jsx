import { useState } from "react";

// Controlled input for composing messages. Supports both the send button and
// the Enter key; empty/whitespace-only input is ignored.
export function MessageInput({ onSend }) {
  const [text, setText] = useState("");

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="chat-input">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type a message..."
        onKeyDown={(e) => e.key === "Enter" && submit()}
      />
      <button onClick={submit} disabled={!text.trim()}>
        Send
      </button>
    </div>
  );
}
