const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const noop = () => {};

function buildUrl(path) {
  if (path.startsWith("http")) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

export function createSseStream({
  path,
  onMessage = noop,
  onError = noop,
  onOpen = noop,
  parse = JSON.parse,
  heartbeatMs = 30000,
} = {}) {
  if (!path) {
    throw new Error("SSE path is required");
  }

  let source = null;
  let heartbeatTimer = null;

  const clearHeartbeat = () => {
    if (heartbeatTimer) {
      clearTimeout(heartbeatTimer);
      heartbeatTimer = null;
    }
  };

  const resetHeartbeat = () => {
    if (!heartbeatMs) return;
    clearHeartbeat();
    heartbeatTimer = setTimeout(() => {
      onError(new Error("SSE heartbeat timeout"));
    }, heartbeatMs);
  };

  const start = () => {
    stop();
    source = new EventSource(buildUrl(path));
    source.onopen = onOpen;
    source.onmessage = (event) => {
      resetHeartbeat();
      if (!event?.data) return;
      try {
        const payload = parse ? parse(event.data) : event.data;
        onMessage(payload);
      } catch (error) {
        onError(error);
      }
    };
    source.onerror = (event) => {
      onError(event instanceof Error ? event : new Error("SSE error"));
    };
    resetHeartbeat();
  };

  const stop = () => {
    clearHeartbeat();
    if (source) {
      source.close();
      source = null;
    }
  };

  return {
    start,
    stop,
  };
}

export function createWorkflowLogStream(workflowId, handlers = {}, options = {}) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  return createSseStream({
    path: `/api/workflows/${workflowId}/logs/stream`,
    ...handlers,
    heartbeatMs: options.heartbeatMs ?? 15000,
  });
}
