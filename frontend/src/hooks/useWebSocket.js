import { useCallback, useEffect, useRef, useState } from "react";

const BASE_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30000;

/**
 * A generic, self-healing WebSocket connection.
 *
 * Responsibilities are deliberately narrow: keep a single socket open to `url`,
 * hand every parsed message to `onMessage`, and transparently reconnect with
 * exponential backoff if the connection drops. It knows nothing about chat
 * semantics — that lives in useChat — so it can carry any future event type.
 *
 * Returns the connection status: "connecting" | "open" | "closed".
 *
 * When `enabled` is false (e.g. mock mode) it never opens a socket and simply
 * reports "open", so the rest of the app needs no special-casing.
 */
export function useWebSocket(url, onMessage, enabled = true) {
  const [status, setStatus] = useState(enabled ? "connecting" : "open");

  // Keep the latest callback in a ref so reconnecting never depends on the
  // caller memoizing onMessage perfectly.
  const onMessageRef = useRef(onMessage);
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const socketRef = useRef(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef(null);
  const activeRef = useRef(true);

  const connect = useCallback(() => {
    setStatus("connecting");
    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onopen = () => {
      attemptRef.current = 0;
      setStatus("open");
    };

    socket.onmessage = (event) => {
      // Ignore a socket that has already been superseded (only the current one
      // delivers), so duplicate sockets can never double-deliver a message.
      if (socketRef.current !== socket) return;
      try {
        onMessageRef.current?.(JSON.parse(event.data));
      } catch (err) {
        console.error("Discarding malformed WebSocket payload", err);
      }
    };

    socket.onerror = () => {
      // Let onclose drive the reconnect; closing here guarantees it fires.
      socket.close();
    };

    socket.onclose = () => {
      // A superseded socket (e.g. from React StrictMode's mount/unmount/remount
      // in dev) must not drive status or spawn a reconnect — only the current
      // one may. This prevents ending up with two live sockets.
      if (socketRef.current !== socket) return;
      setStatus("closed");
      if (!activeRef.current) return;
      const delay = Math.min(
        BASE_BACKOFF_MS * 2 ** attemptRef.current,
        MAX_BACKOFF_MS
      );
      attemptRef.current += 1;
      reconnectTimerRef.current = setTimeout(connect, delay);
    };
  }, [url]);

  useEffect(() => {
    if (!enabled) return undefined;
    activeRef.current = true;
    connect();
    return () => {
      // Stop reconnect attempts and tear down on unmount / url change.
      activeRef.current = false;
      clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
    };
  }, [connect, enabled]);

  return status;
}
