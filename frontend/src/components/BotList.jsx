export function BotList({ bots, selectedBotUsername, unreadByBotUsername, onSelect }) {
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
          const unread = unreadByBotUsername?.[bot.username] || 0;
          const activeChats = bot.active_chats ?? 0;
          const capacityLabel = isPrivate
            ? "Private"
            : `${activeChats}/${bot.max_chats}`;
          const capacityTitle = isPrivate
            ? "Single-user bot"
            : `${activeChats} of ${bot.max_chats} active conversations`;

          return (
            <li key={bot.bot_id}>
              <button
                type="button"
                className={`inbox-list-item${active ? " active" : ""}`}
                onClick={() => onSelect(bot.username)}
              >
                <div className="inbox-list-item-row">
                  <span className="inbox-list-item-title">{bot.bot_name}</span>
                  <span className="bot-meta-badge" title={capacityTitle}>
                    {capacityLabel}
                  </span>
                </div>
                <div className="inbox-list-item-row">
                  <span className="inbox-list-item-subtitle">@{bot.username}</span>
                  <span className="inbox-list-item-trailing">
                    {unread > 0 && (
                      <span className="inbox-unread-badge">{unread}</span>
                    )}
                  </span>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
