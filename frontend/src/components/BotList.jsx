export function BotList({ bots, selectedBotUsername, onSelect }) {
  return (
    <aside className="inbox-panel inbox-panel--bots">
      <div className="inbox-panel-header">
        <h2>Bots</h2>
      </div>
      <ul className="inbox-list">
        {bots.length === 0 && (
          <li className="inbox-empty">No bots configured</li>
        )}
        {bots.map((bot) => {
          const active = bot.username === selectedBotUsername;
          const isPrivate = bot.max_chats === 1;
          return (
            <li key={bot.bot_id}>
              <button
                type="button"
                className={`inbox-list-item${active ? " active" : ""}`}
                onClick={() => onSelect(bot.username)}
              >
                <div className="inbox-list-item-row">
                  <span className="inbox-list-item-title">{bot.bot_name}</span>
                  {isPrivate && (
                    <span className="bot-private-badge" title="Single-user bot">
                      Private
                    </span>
                  )}
                </div>
                <span className="inbox-list-item-subtitle">@{bot.username}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
