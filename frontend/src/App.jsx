import { BrowserRouter, Route, Routes } from "react-router-dom";
import "./index.css";
import { InboxPage } from "./pages/InboxPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<InboxPage />} />
        <Route path="/bots/:botUsername" element={<InboxPage />} />
        <Route
          path="/bots/:botUsername/chats/:chatId"
          element={<InboxPage />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
