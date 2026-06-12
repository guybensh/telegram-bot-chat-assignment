import { ConnectionStatus } from "./ConnectionStatus";

export function ChatHeader({ connectionStatus, onReset }) {
  return (
    <header className="chat-header">
      <h2>Telegram Chat</h2>
      <div className="chat-header-right">
        <ConnectionStatus status={connectionStatus} />
        <button
          className="reset-button"
          onClick={onReset}
          title="Clear the active conversation (dev/admin)"
        >
          Reset
        </button>
      </div>
    </header>
  );
}
