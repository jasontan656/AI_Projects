import { requestJson } from "./httpClient";

const sanitizePolicyPayload = (payload = {}) => {
  const enforced = {
    channel: "telegram",
    webhookUrl: payload.webhookUrl || "",
    waitForResult: Boolean(payload.waitForResult),
    workflowMissingMessage: payload.workflowMissingMessage || "",
    timeoutMessage: payload.timeoutMessage || "",
    metadata: {
      allowedChatIds: Array.isArray(payload.metadata?.allowedChatIds)
        ? payload.metadata.allowedChatIds.map((id) => String(id).trim()).filter(Boolean)
        : [],
      rateLimitPerMin: Number.isFinite(payload.metadata?.rateLimitPerMin)
        ? payload.metadata.rateLimitPerMin
        : 60,
      locale: payload.metadata?.locale || "zh-CN",
    },
  };

  const trimmedToken = typeof payload.botToken === "string" ? payload.botToken.trim() : payload.botToken;
  if (trimmedToken) {
    enforced.botToken = trimmedToken;
  }

  return enforced;
};

const extractPolicy = (response) =>
  response?.data?.channelPolicy ?? response?.data ?? null;

export async function getChannelPolicy(workflowId) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const response = await requestJson(
    `/api/workflow-channels/${workflowId}?channel=telegram`,
    { method: "GET" }
  );
  return extractPolicy(response);
}

export async function saveChannelPolicy(workflowId, payload = {}) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const body = {
    workflowId,
    ...sanitizePolicyPayload(payload),
  };
  const response = await requestJson(`/api/workflow-channels/${workflowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return extractPolicy(response);
}

export async function deleteChannelPolicy(workflowId) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  await requestJson(`/api/workflow-channels/${workflowId}?channel=telegram`, {
    method: "DELETE",
  });
}

export async function fetchChannelHealth(workflowId, options = {}) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const query = new URLSearchParams();
  query.set("workflowId", workflowId);
  if (options.includeMetrics !== false) {
    query.set("includeMetrics", "true");
  }
  const response = await requestJson(
    `/api/channels/telegram/health?${query.toString()}`,
    { method: "GET" }
  );
  return response || null;
}

export async function sendChannelTest(payload = {}) {
  if (!payload.workflowId) {
    throw new Error("缺少 workflowId");
  }
  if (!payload.chatId) {
    throw new Error("chatId 不能为空");
  }
  const response = await requestJson("/api/channels/telegram/test", {
    method: "POST",
    body: JSON.stringify({
      workflowId: payload.workflowId,
      chatId: payload.chatId,
      payloadText: payload.payloadText || "",
      waitForResult: Boolean(payload.waitForResult),
      correlationId: payload.correlationId,
    }),
  });
  return response || null;
}
