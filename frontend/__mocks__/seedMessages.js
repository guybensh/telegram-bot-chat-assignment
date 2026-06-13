// Sample conversation used only in mock mode (VITE_USE_MOCK=true) so the UI can
// be demoed without a running backend. Timestamps are relative to load time so
// the chat always looks recent.
const minutesAgo = (n) => new Date(Date.now() - n * 60_000).toISOString();

// A stand-in Telegram chat id for the seeded conversation in mock mode.
export const MOCK_CHAT_ID = 424242;

export const seedMessages = [
  {
    id: "seed-1",
    chat_id: MOCK_CHAT_ID,
    text: "Hey! Is this the support bot?",
    timestamp: minutesAgo(6),
    sender: "user", // remote Telegram participant
    status: "received",
  },
  {
    id: "seed-2",
    chat_id: MOCK_CHAT_ID,
    text: "Yes — how can I help?",
    timestamp: minutesAgo(5),
    sender: "agent", // our web app (the human agent)
    status: "sent",
  },
  {
    id: "seed-3",
    chat_id: MOCK_CHAT_ID,
    text: "Great, just testing the chat 👍",
    timestamp: minutesAgo(4),
    sender: "user",
    status: "received",
  },
];
