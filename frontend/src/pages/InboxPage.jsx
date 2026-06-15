import { useNavigate, useParams } from "react-router-dom";
import { useInbox } from "../hooks/useInbox";
import { BotList } from "../components/BotList";
import { ConversationList } from "../components/ConversationList";
import { Chat } from "../components/Chat";
import { ConnectionStatus } from "../components/ConnectionStatus";

export function InboxPage() {
  const { botUsername, chatId: chatIdParam } = useParams();
  const navigate = useNavigate();
  const chatId = chatIdParam ?? null;

  const {
    bots,
    conversations,
    selectedConversation,
    messages,
    connectionStatus,
    send,
    canSend,
    reset,
    unreadByChatId,
    unreadByBotUsername,
  } = useInbox(botUsername, chatId);

  const handleSelectBot = (username) => {
    navigate(`/bots/${username}`);
  };

  const handleSelectConversation = (id) => {
    if (!botUsername) return;
    navigate(`/bots/${botUsername}/chats/${id}`);
  };

  const handleReset = async () => {
    await reset();
    if (botUsername) navigate(`/`, { replace: true });
  };

  return (
    <div className="inbox-page">
      <div className="inbox-page-inner">
        <div className="inbox-toolbar">
          <div className="inbox-toolbar-actions">
            <button
              type="button"
              className="inbox-toolbar-button"
              onClick={() => navigate("/")}
              title="Back to inbox home"
            >
              Home
            </button>
            <button
              type="button"
              className="inbox-toolbar-button inbox-toolbar-button--danger"
              onClick={handleReset}
              title="Clear all conversations (dev/admin)"
            >
              Reset
            </button>
          </div>
          <ConnectionStatus status={connectionStatus} />
        </div>
        <div className="inbox-shell">
          <BotList
            bots={bots}
            selectedBotUsername={botUsername}
            unreadByBotUsername={unreadByBotUsername}
            onSelect={handleSelectBot}
          />
          <ConversationList
            botUsername={botUsername}
            conversations={conversations}
            selectedChatId={chatId}
            unreadByChatId={unreadByChatId}
            onSelect={handleSelectConversation}
          />
          <Chat
            botUsername={botUsername}
            conversation={selectedConversation}
            messages={messages}
            canSend={canSend}
            onSend={send}
          />
        </div>
      </div>
    </div>
  );
}
