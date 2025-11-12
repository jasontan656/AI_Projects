import { CHANNEL_HEALTH_DEFAULTS } from "../schemas/channelPolicy.js";

const noop = () => {};

export function createChannelHealthScheduler({
  poller,
  baseIntervalMs = CHANNEL_HEALTH_DEFAULTS.baseIntervalMs,
  maxIntervalMs = CHANNEL_HEALTH_DEFAULTS.maxIntervalMs,
  maxFailures = CHANNEL_HEALTH_DEFAULTS.maxFailures,
} = {}) {
  if (typeof poller !== "function") {
    throw new Error("poller function is required for ChannelHealthScheduler");
  }

  let timer = null;
  let currentWorkflowId = null;
  let failureCount = 0;
  let paused = false;
  let nextInterval = baseIntervalMs;
  let handlers = {
    onSuccess: noop,
    onFailure: noop,
    onPause: noop,
  };

  const clearTimer = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const scheduleNext = () => {
    clearTimer();
    if (!currentWorkflowId || paused) {
      return;
    }
    timer = setTimeout(() => {
      void tick({ silent: true });
    }, nextInterval);
  };

  const tick = async ({ silent = false } = {}) => {
    if (!currentWorkflowId) {
      return;
    }
    try {
      const data = await poller(currentWorkflowId, { silent });
      failureCount = 0;
      paused = false;
      nextInterval = baseIntervalMs;
      handlers.onSuccess?.(data);
      scheduleNext();
    } catch (error) {
      failureCount += 1;
      handlers.onFailure?.(error, failureCount);
      if (failureCount >= maxFailures) {
        paused = true;
        clearTimer();
        handlers.onPause?.(error, failureCount);
        return;
      }
      const backoff = baseIntervalMs * Math.pow(2, failureCount - 1);
      nextInterval = Math.min(backoff, maxIntervalMs);
      scheduleNext();
    }
  };

  const start = (workflowId, nextHandlers = {}) => {
    clearTimer();
    currentWorkflowId = workflowId || null;
    failureCount = 0;
    paused = false;
    nextInterval = baseIntervalMs;
    handlers = {
      onSuccess: nextHandlers.onSuccess || noop,
      onFailure: nextHandlers.onFailure || noop,
      onPause: nextHandlers.onPause || noop,
    };
    if (!currentWorkflowId) {
      return;
    }
    void tick({ silent: false });
  };

  const stop = () => {
    clearTimer();
    currentWorkflowId = null;
    paused = false;
    failureCount = 0;
  };

  const refresh = ({ silent = false } = {}) => {
    clearTimer();
    return tick({ silent });
  };

  return {
    start,
    stop,
    refresh,
    getState: () => ({
      paused,
      failureCount,
      nextInterval,
    }),
  };
}
