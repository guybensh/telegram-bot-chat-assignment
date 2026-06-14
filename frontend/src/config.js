// Central place for backend connection details.
// VITE_API_URL is injected at build/dev time (see docker-compose.yml); it
// defaults to the local backend so `npm run dev` works with no extra config.
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// The WebSocket endpoint lives on the same host as the REST API. We derive it
// from API_URL so there is a single source of truth: http -> ws, https -> wss.
export const WS_URL = `${API_URL.replace(/^http/, "ws")}/ws`;

// Mock mode lets the UI run with no backend: it seeds sample messages and
// echoes replies locally (see hooks/useInbox.js). Enable with `npm run dev:mock`.
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
