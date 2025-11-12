const CHANNEL_POLICY_DEFAULT = {
  workflowId: null,
  channel: "telegram",
  botToken: "",
  maskedBotToken: "",
  webhookUrl: "",
  waitForResult: true,
  workflowMissingMessage: "",
  timeoutMessage: "",
  metadata: {
    allowedChatIds: [],
    rateLimitPerMin: 60,
    locale: "zh-CN",
  },
  updatedAt: null,
  updatedBy: null,
};

export const CHANNEL_TEST_RULE = {
  maxAttempts: 3,
  windowMs: 60_000,
};

export const CHANNEL_HEALTH_DEFAULTS = {
  baseIntervalMs: 30_000,
  maxIntervalMs: 120_000,
  maxFailures: 3,
};

const toCleanString = (value) => {
  if (typeof value !== "string") return "";
  return value.trim();
};

const normalizeChatIds = (ids) => {
  if (!Array.isArray(ids)) return [];
  return ids
    .map((id) => toCleanString(String(id)))
    .filter((id) => id.length > 0);
};

export function createChannelPolicy(overrides = {}) {
  const merged = {
    ...CHANNEL_POLICY_DEFAULT,
    ...overrides,
    metadata: {
      ...CHANNEL_POLICY_DEFAULT.metadata,
      ...(overrides?.metadata || {}),
    },
  };
  merged.metadata.allowedChatIds = normalizeChatIds(
    merged.metadata.allowedChatIds
  );
  merged.metadata.rateLimitPerMin = Number.isFinite(
    merged.metadata.rateLimitPerMin
  )
    ? merged.metadata.rateLimitPerMin
    : CHANNEL_POLICY_DEFAULT.metadata.rateLimitPerMin;
  merged.metadata.locale =
    merged.metadata.locale || CHANNEL_POLICY_DEFAULT.metadata.locale;
  return merged;
}

export function normalizeChannelPolicyResponse(response) {
  if (!response) {
    return createChannelPolicy();
  }
  return createChannelPolicy({
    ...response,
    botToken: response.botToken || "",
    maskedBotToken: response.maskedBotToken || "",
    updatedAt: response.updatedAt || null,
    updatedBy: response.updatedBy || null,
  });
}

export function buildChannelPolicyPayload(payload = {}) {
  const normalized = createChannelPolicy(payload);
  const body = {
    channel: normalized.channel,
    webhookUrl: normalized.webhookUrl,
    waitForResult: Boolean(normalized.waitForResult),
    workflowMissingMessage: normalized.workflowMissingMessage,
    timeoutMessage: normalized.timeoutMessage,
    metadata: {
      allowedChatIds: normalized.metadata.allowedChatIds,
      rateLimitPerMin: normalized.metadata.rateLimitPerMin,
      locale: normalized.metadata.locale,
    },
  };
  const trimmedToken = toCleanString(payload.botToken ?? normalized.botToken);
  if (trimmedToken) {
    body.botToken = trimmedToken;
  }
  return body;
}

export function createTestThrottleState(attempts = []) {
  return {
    attempts: attempts
      .filter((ts) => Number.isFinite(ts))
      .map((ts) => Number(ts)),
  };
}

export function pruneTestAttempts(state, now = Date.now()) {
  state.attempts = state.attempts.filter(
    (ts) => now - ts < CHANNEL_TEST_RULE.windowMs
  );
  return state;
}

export function canSendTest(state, now = Date.now()) {
  pruneTestAttempts(state, now);
  return state.attempts.length < CHANNEL_TEST_RULE.maxAttempts;
}

export function recordTestAttempt(state, timestamp = Date.now()) {
  pruneTestAttempts(state, timestamp);
  state.attempts = [...state.attempts, timestamp];
  return state;
}

export function getTestCooldownUntil(state, now = Date.now()) {
  pruneTestAttempts(state, now);
  if (state.attempts.length < CHANNEL_TEST_RULE.maxAttempts) {
    return 0;
  }
  const oldest = state.attempts[0];
  return oldest + CHANNEL_TEST_RULE.windowMs;
}
