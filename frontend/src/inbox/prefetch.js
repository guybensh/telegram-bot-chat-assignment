import { fetchChatSummaries, fetchMessages } from "../api/client";
import { threadKey } from "./keys";

/**
 * Load conversation list and message history for every active thread on a bot.
 * Does not mark messages read — that happens only when the agent opens a thread.
 */
export async function prefetchBotThreadHistories(botUsername, dispatch) {
  const conversations = await fetchChatSummaries(botUsername);
  dispatch({
    type: "CONVERSATIONS_LOADED",
    botUsername,
    conversations,
  });

  await Promise.all(
    conversations.map(async (conversation) => {
      const history = await fetchMessages(botUsername, conversation.chat_id);
      dispatch({
        type: "THREAD_HISTORY_LOADED",
        threadKey: threadKey(botUsername, conversation.chat_id),
        history,
      });
    })
  );
}
