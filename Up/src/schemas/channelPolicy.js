const CHANNEL_POLICY_DEFAULT = {
  workflowId: null,
  channel: "telegram",
  botToken: "",
  maskedBotToken: "",
  webhookUrl: "",
  waitForResult: true,
  workflowMissingMessage: "",
  timeoutMessage: "",
  usePolling: false,
  metadata: {
    allowedChatIds: [],
    rateLimitPerMin: 60,
    locale: "zh-CN",
  },
  security: {
    secret: "",
    certificatePem: "",
    certificateName: "",
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
  const segmented = { ...overrides };
  if (overrides?.credential) {
    const credential = overrides.credential;
    segmented.botToken = credential.botToken ?? overrides.botToken ?? "";
    segmented.maskedBotToken =
      credential.maskedBotToken ?? overrides.maskedBotToken ?? "";
    segmented.webhookUrl =
      credential.webhookUrl ?? overrides.webhookUrl ?? "";
    segmented.waitForResult =
      credential.waitForResult ?? overrides.waitForResult ?? true;
    segmented.workflowMissingMessage =
      credential.workflowMissingMessage ??
      overrides.workflowMissingMessage ??
      "";
    segmented.timeoutMessage =
      credential.timeoutMessage ?? overrides.timeoutMessage ?? "";
    segmented.usePolling = Boolean(
      credential.usePolling ?? overrides.usePolling ?? false,
    );
  }
  if (overrides?.rateLimit) {
    segmented.metadata = {
      ...(overrides?.metadata || {}),
      ...overrides.rateLimit,
    };
  }
  if (overrides?.security) {
    segmented.security = {
      ...CHANNEL_POLICY_DEFAULT.security,
      ...overrides.security,
    };
  }

  const merged = {
    ...CHANNEL_POLICY_DEFAULT,
    ...segmented,
    metadata: {
      ...CHANNEL_POLICY_DEFAULT.metadata,
      ...(segmented?.metadata || {}),
    },
    security: {
      ...CHANNEL_POLICY_DEFAULT.security,
      ...(segmented?.security || {}),
    },
  };
  merged.usePolling = Boolean(overrides?.usePolling ?? CHANNEL_POLICY_DEFAULT.usePolling);
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
  const payload = {
    ...response,
    botToken: response.botToken || "",
    maskedBotToken: response.maskedBotToken || "",
    updatedAt: response.updatedAt || null,
    updatedBy: response.updatedBy || null,
    usePolling: Boolean(response.usePolling),
  };
  if (response.credential) {
    Object.assign(payload, {
      botToken: response.credential.botToken || payload.botToken,
      maskedBotToken:
        response.credential.maskedBotToken || payload.maskedBotToken,
      webhookUrl: response.credential.webhookUrl ?? payload.webhookUrl,
      waitForResult:
        response.credential.waitForResult ?? payload.waitForResult,
      workflowMissingMessage:
        response.credential.workflowMissingMessage ??
        payload.workflowMissingMessage,
      timeoutMessage:
        response.credential.timeoutMessage ?? payload.timeoutMessage,
      usePolling:
        response.credential.usePolling ?? payload.usePolling ?? false,
    });
  }
  if (response.rateLimit) {
    payload.metadata = {
      ...payload.metadata,
      ...response.rateLimit,
    };
  }
  if (response.security) {
    payload.security = {
      ...payload.security,
      ...response.security,
    };
  }
  return createChannelPolicy(payload);
}

export function buildChannelPolicyPayload(payload = {}) {
  const normalized = createChannelPolicy(payload);
  const credential = {
    webhookUrl: normalized.usePolling ? "" : normalized.webhookUrl,
    waitForResult: Boolean(normalized.waitForResult),
    workflowMissingMessage: normalized.workflowMissingMessage,
    timeoutMessage: normalized.timeoutMessage,
    usePolling: Boolean(normalized.usePolling),
  };
  const trimmedToken = toCleanString(payload.botToken ?? normalized.botToken);
  if (trimmedToken) {
    credential.botToken = trimmedToken;
  }

  const rateLimit = {
    allowedChatIds: normalized.metadata.allowedChatIds
      .map((id) => id.trim())
      .filter((id) => id.length > 0),
    rateLimitPerMin: normalized.metadata.rateLimitPerMin,
    locale: normalized.metadata.locale,
  };

  const security = {
    secret: normalized.security?.secret || "",
    certificatePem: normalized.security?.certificatePem || "",
    certificateName: normalized.security?.certificateName || "",
  };

  const body = {
    channel: normalized.channel,
    credential,
    rateLimit,
    security,
  };

  // Legacy fields kept for backward compatibility while backend migrates.
  body.webhookUrl = credential.webhookUrl;
  body.waitForResult = credential.waitForResult;
  body.workflowMissingMessage = credential.workflowMissingMessage;
  body.timeoutMessage = credential.timeoutMessage;
  body.usePolling = credential.usePolling;
  body.metadata = rateLimit;
  if (credential.botToken) {
    body.botToken = credential.botToken;
  }
  if (security.secret) {
    body.webhookSecret = security.secret;
  }
  if (security.certificatePem) {
    body.certificatePem = security.certificatePem;
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
