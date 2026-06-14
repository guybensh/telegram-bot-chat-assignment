import { useEffect } from "react";
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
  } = useInbox(botUsername, chatId);

  useEffect(() => {
    if (bots.length === 0) return;
    if (
      !botUsername ||
      !bots.some((bot) => bot.username === botUsername)
    ) {
      navigate(`/bots/${bots[0].username}`, { replace: true });
    }
  }, [bots, botUsername, navigate]);

  useEffect(() => {
    if (chatId != null || !botUsername || conversations.length !== 1) return;
    navigate(`/bots/${botUsername}/chats/${conversations[0].chat_id}`, {
      replace: true,
    });
  }, [chatId, botUsername, conversations, navigate]);

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
      <div className="inbox-shell">
        <BotList
          bots={bots}
          selectedBotUsername={botUsername}
          onSelect={handleSelectBot}
        />
        <ConversationList
          conversations={conversations}
          selectedChatId={chatId}
          unreadByChatId={unreadByChatId}
          onSelect={handleSelectConversation}
        />
        <ConversationPanel
          conversation={selectedConversation}
          messages={messages}
          connectionStatus={connectionStatus}
          canSend={canSend}
          onSend={send}
          onReset={handleReset}
        />
      </div>
    </div>
  );
}
