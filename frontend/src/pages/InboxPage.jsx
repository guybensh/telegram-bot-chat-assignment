import { useNavigate, useParams } from "react-router-dom";
import { useInbox } from "../hooks/useInbox";
import { BotList } from "../components/BotList";
import { ConversationList } from "../components/ConversationList";
import { ConversationPanel } from "../components/ConversationPanel";

export function InboxPage() {
  const { botUsername, chatId: chatIdParam } = useParams();
  const navigate = useNavigate();
  const chatId = chatIdParam ? Number(chatIdParam) : null;

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
    if (botUsername) navigate(`/bots/${botUsername}`, { replace: true });
  };

  return (
    <div className="inbox-page">
      <div className="inbox-page-inner">
        <div className="inbox-toolbar">
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
          <ConversationPanel
            botUsername={botUsername}
            conversation={selectedConversation}
            messages={messages}
            connectionStatus={connectionStatus}
            canSend={canSend}
            onSend={send}
          />
        </div>
      </div>
    </div>
  );
}
