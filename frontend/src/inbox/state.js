import { USE_MOCK } from "../config";
import {
  buildMockBots,
  buildMockMessagesByThread,
  mockConversationsForBot,
} from "./mock";

export const emptyInboxState = () => ({
  bots: [],
  conversations: [],
  messagesByThread: {},
  unreadByChatId: {},
  unreadByBotUsername: {},
});

export function createInitialInboxState(botUsername) {
  if (!USE_MOCK) return emptyInboxState();
  return {
    bots: buildMockBots(),
    conversations: botUsername ? mockConversationsForBot(botUsername) : [],
    messagesByThread: buildMockMessagesByThread(),
    unreadByChatId: {},
    unreadByBotUsername: {},
  };
}
