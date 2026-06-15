export const emptyInboxState = () => ({
  bots: [],
  conversationsByBot: {},
  messagesByThread: {},
});

export function createInitialInboxState() {
  return emptyInboxState();
}
