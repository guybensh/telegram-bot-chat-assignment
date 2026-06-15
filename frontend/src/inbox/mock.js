import {
  mockBots,
  mockConversations,
  seedMessagesByChat,
} from "../../__mocks__/seedMessages";
import { threadKey } from "./keys";

export function buildMockBots() {
  return mockBots.map((bot) => ({
    ...bot,
    active_chats: mockConversations.filter(
      (conversation) => conversation.bot_username === bot.username
    ).length,
  }));
}

export function buildMockMessagesByThread() {
  const out = {};
  for (const conversation of mockConversations) {
    const messages = seedMessagesByChat[conversation.chat_id];
    if (messages) {
      out[threadKey(conversation.bot_username, conversation.chat_id)] = messages;
    }
  }
  return out;
}

export function mockConversationsForBot(botUsername) {
  return mockConversations.filter((c) => c.bot_username === botUsername);
}
