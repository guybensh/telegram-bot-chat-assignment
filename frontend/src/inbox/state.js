import { USE_MOCK } from "../config";
import {
  buildMockBots,
  buildMockMessagesByThread,
  mockConversationsForBot,
} from "./mock";

export const emptyInboxState = () => ({
  bots: [],
  conversationsByBot: {},
  messagesByThread: {},
  unreadByChatId: {},
  unreadByBotUsername: {},
});

export function createInitialInboxState(botUsername) {
  if (!USE_MOCK) return emptyInboxState();
  return {
    bots: buildMockBots(),
    conversationsByBot: botUsername
      ? { [botUsername]: mockConversationsForBot(botUsername) }
      : {},
    messagesByThread: buildMockMessagesByThread(),
    unreadByChatId: {},
    unreadByBotUsername: {},
  };
}
