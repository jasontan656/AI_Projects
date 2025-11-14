const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const noop = () => {};
const decoder = new TextDecoder("utf-8");

function buildUrl(path) {
  if (path.startsWith("http")) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}

function parseRetryAfter(headers) {
  const retryMs = headers.get("retry-after-ms");
  if (retryMs && !Number.isNaN(Number(retryMs))) {
    return Number(retryMs);
  }
  const retryAfter = headers.get("retry-after");
  if (!retryAfter) {
    return null;
  }
  if (/^\d+$/.test(retryAfter)) {
    return Number(retryAfter) * 1000;
  }
  const future = Date.parse(retryAfter);
  if (Number.isNaN(future)) {
    return null;
  }
  return Math.max(0, future - Date.now());
}

function parseEventChunks(buffer) {
  const events = [];
  let searchIndex;
  while ((searchIndex = buffer.indexOf("\n\n")) !== -1) {
    const rawEvent = buffer.slice(0, searchIndex);
    buffer = buffer.slice(searchIndex + 2);
    const lines = rawEvent.split(/\r?\n/);
    const dataLines = [];
    for (const line of lines) {
      if (!line || line.startsWith(":")) continue;
      const [field, ...rest] = line.split(":");
      const value = rest.join(":").replace(/^\s+/, "");
      if (field === "data") {
        dataLines.push(value);
      }
    }
    if (dataLines.length) {
      events.push(dataLines.join("\n"));
    }
  }
  return { events, buffer };
}

export function createSseStream({
  path,
  onMessage = noop,
  onError = noop,
  onOpen = noop,
  onRetry = noop,
  parse = JSON.parse,
  heartbeatMs = 30000,
} = {}) {
  if (!path) {
    throw new Error("SSE path is required");
  }

  let abortController = null;
  let heartbeatTimer = null;
  let reader = null;
  let buffer = "";

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

  const closeReader = () => {
    if (reader) {
      reader.releaseLock?.();
      reader = null;
    }
  };

  const start = async () => {
    stop();
    abortController = new AbortController();
    buffer = "";
    try {
      const response = await fetch(buildUrl(path), {
        headers: { Accept: "text/event-stream" },
        signal: abortController.signal,
      });

      if (!response.ok || !response.body) {
        const retryAfterMs = parseRetryAfter(response.headers);
        if (retryAfterMs !== null) {
          onRetry({ retryAfterMs });
        }
        onError(new Error(`SSE请求失败: ${response.status}`));
        return;
      }

      onOpen(response);
      reader = response.body.getReader();
      resetHeartbeat();

      /* eslint-disable no-constant-condition */
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          throw new Error("SSE 流已结束");
        }
        resetHeartbeat();
        buffer += decoder.decode(value, { stream: true });
        const parsed = parseEventChunks(buffer);
        buffer = parsed.buffer;
        for (const chunk of parsed.events) {
          try {
            const payload = parse ? parse(chunk) : chunk;
            onMessage(payload);
          } catch (error) {
            onError(error);
          }
        }
      }
      /* eslint-enable no-constant-condition */
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      onError(error);
    } finally {
      clearHeartbeat();
      closeReader();
    }
  };

  const stop = () => {
    clearHeartbeat();
    if (abortController) {
      abortController.abort();
      abortController = null;
    }
    closeReader();
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
