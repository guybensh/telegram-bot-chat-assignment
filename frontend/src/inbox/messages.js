import { normalizeMessage } from "./normalize";

export function appendToThread(threads, key, message) {
  return {
    ...threads,
    [key]: [...(threads[key] || []), normalizeMessage(message)],
  };
}

export function updateMessageStatus(threads, key, messageId, status) {
  const thread = threads[key];
  if (!thread) return threads;
  return {
    ...threads,
    [key]: thread.map((m) => (m.id === messageId ? { ...m, status } : m)),
  };
}
