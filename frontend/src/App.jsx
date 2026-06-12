import "./index.css";
import { useChat } from "./hooks/useChat";
import { ChatHeader } from "./components/ChatHeader";
import { MessageList } from "./components/MessageList";
import { MessageInput } from "./components/MessageInput";

// Composition root: wire the chat state from useChat into the presentational
// components. App holds no logic of its own, which keeps the data flow obvious.
function App() {
  const { messages, connectionStatus, send } = useChat();

  return (
    <div className="chat-page">
      <div className="chat-container">
        <ChatHeader connectionStatus={connectionStatus} />
        <MessageList messages={messages} />
        <MessageInput onSend={send} />
      </div>
    </div>
  );
}

export default App;
