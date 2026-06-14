import { ConnectionStatus } from "./ConnectionStatus";

export function ChatHeader({ title, connectionStatus }) {
  return (
    <header className="inbox-panel-header">
      <h2>{title}</h2>
      {connectionStatus != null && (
        <div className="inbox-panel-header-actions">
          <ConnectionStatus status={connectionStatus} />
        </div>
      )}
    </header>
  );
}
