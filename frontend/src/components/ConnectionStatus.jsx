const LABELS = {
  connecting: "Connecting…",
  open: "Connected",
  closed: "Reconnecting…",
};

// Small live indicator so the user knows whether incoming messages can arrive.
export function ConnectionStatus({ status }) {
  return (
    <span className={`connection-status ${status}`}>
      <span className="connection-dot" />
      {LABELS[status] ?? status}
    </span>
  );
}
