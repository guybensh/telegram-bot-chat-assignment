import { useState } from "react";

// Controlled input for composing messages. Supports both the send button and
// the Enter key; empty/whitespace-only input is ignored.
//
// When `disabled` (no active conversation yet — a Telegram bot can't initiate),
// the composer is locked with a hint, since there's no one to send to.
export function MessageInput({ onSend, disabled }) {
  const [text, setText] = useState("");

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
  };

  return (
    <div className="chat-input">
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={
          disabled
            ? "Waiting for a user to start the chat…"
            : "Type a message..."
        }
        onKeyDown={(e) => e.key === "Enter" && submit()}
        disabled={disabled}
      />
      <button onClick={submit} disabled={disabled || !text.trim()}>
        Send
      </button>
    </div>
  );
}
