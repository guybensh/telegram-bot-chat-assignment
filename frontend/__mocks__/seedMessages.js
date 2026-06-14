// Sample data for mock mode (VITE_USE_MOCK=true) so the inbox UI can be demoed
// without a running backend.

const minutesAgo = (n) => new Date(Date.now() - n * 60_000).toISOString();

export const MOCK_BOT_USERNAME = "support_bot";

export const mockBots = [
  {
    bot_id: 1001,
    bot_name: "Support Bot",
    username: MOCK_BOT_USERNAME,
    max_chats: 10,
    private: false,
  },
  {
    bot_id: 1002,
    bot_name: "VIP Bot",
    username: "vip_bot",
    max_chats: 1,
    private: true,
  },
];

export const MOCK_CHAT_ID = 424242;
export const MOCK_CHAT_ID_2 = 515151;

export const mockConversations = [
  {
    chat_id: MOCK_CHAT_ID,
    bot_id: 1001,
    bot_username: MOCK_BOT_USERNAME,
    title: `Chat ${MOCK_CHAT_ID}`,
    last_message_text: "Great, just testing the chat 👍",
    last_message_at: minutesAgo(4),
    last_sender: "user",
  },
  {
    chat_id: MOCK_CHAT_ID_2,
    bot_id: 1001,
    bot_username: MOCK_BOT_USERNAME,
    title: `Chat ${MOCK_CHAT_ID_2}`,
    last_message_text: "Can you help me with my order?",
    last_message_at: minutesAgo(12),
    last_sender: "user",
  },
];

export const seedMessagesByChat = {
  [MOCK_CHAT_ID]: [
    {
      id: "seed-1",
      bot_id: 1001,
      chat_id: MOCK_CHAT_ID,
      text: "Hey! Is this the support bot?",
      timestamp: minutesAgo(6),
      sender: "user",
      status: "received",
    },
    {
      id: "seed-2",
      bot_id: 1001,
      chat_id: MOCK_CHAT_ID,
      text: "Yes — how can I help?",
      timestamp: minutesAgo(5),
      sender: "agent",
      status: "sent",
    },
    {
      id: "seed-3",
      bot_id: 1001,
      chat_id: MOCK_CHAT_ID,
      text: "Great, just testing the chat 👍",
      timestamp: minutesAgo(4),
      sender: "user",
      status: "received",
    },
  ],
  [MOCK_CHAT_ID_2]: [
    {
      id: "seed-4",
      bot_id: 1001,
      chat_id: MOCK_CHAT_ID_2,
      text: "Hi there",
      timestamp: minutesAgo(15),
      sender: "user",
      status: "received",
    },
    {
      id: "seed-5",
      bot_id: 1001,
      chat_id: MOCK_CHAT_ID_2,
      text: "Hello! What can I do for you?",
      timestamp: minutesAgo(14),
      sender: "agent",
      status: "sent",
    },
    {
      id: "seed-6",
      bot_id: 1001,
      chat_id: MOCK_CHAT_ID_2,
      text: "Can you help me with my order?",
      timestamp: minutesAgo(12),
      sender: "user",
      status: "received",
    },
  ],
};

export const seedMessages = seedMessagesByChat[MOCK_CHAT_ID];
