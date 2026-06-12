import { ConnectionStatus } from "./ConnectionStatus";

export function ChatHeader({ connectionStatus }) {
  return (
    <header className="chat-header">
      <h2>Telegram Chat</h2>
      <ConnectionStatus status={connectionStatus} />
    </header>
  );
}
