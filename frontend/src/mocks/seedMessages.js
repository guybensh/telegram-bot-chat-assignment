// Sample conversation used only in mock mode (VITE_USE_MOCK=true) so the UI can
// be demoed without a running backend. Timestamps are relative to load time so
// the chat always looks recent.
const minutesAgo = (n) => new Date(Date.now() - n * 60_000).toISOString();

export const seedMessages = [
  {
    id: "seed-1",
    text: "Hey! Is this the support bot?",
    timestamp: minutesAgo(6),
    sender: "bot",
    status: "received",
  },
  {
    id: "seed-2",
    text: "Yes — you're connected. How can I help?",
    timestamp: minutesAgo(5),
    sender: "user",
    status: "sent",
  },
  {
    id: "seed-3",
    text: "Great, just testing the chat 👍",
    timestamp: minutesAgo(4),
    sender: "bot",
    status: "received",
  },
];
