import { requestJson } from "./httpClient";
import {
  buildChannelPolicyPayload,
  normalizeChannelPolicyResponse,
} from "../schemas/channelPolicy.js";

const ensureWorkflowId = (workflowId) => {
  if (!workflowId) {
    throw new Error("workflow 未发布，无法绑定渠道");
  }
  return workflowId;
};

export async function fetchChannelPolicy(workflowId) {
  ensureWorkflowId(workflowId);
  const response = await requestJson(
    `/api/workflow-channels/${workflowId}?channel=telegram`,
    { method: "GET" }
  );
  return normalizeChannelPolicyResponse(response?.data ?? response);
}

export async function saveChannelPolicy(workflowId, payload = {}) {
  ensureWorkflowId(workflowId);
  const body = {
    workflowId,
    ...buildChannelPolicyPayload(payload),
  };
  const response = await requestJson(`/api/workflow-channels/${workflowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return normalizeChannelPolicyResponse(response?.data ?? response);
}

export async function deleteChannelPolicy(workflowId) {
  ensureWorkflowId(workflowId);
  await requestJson(`/api/workflow-channels/${workflowId}?channel=telegram`, {
    method: "DELETE",
  });
}

export async function fetchChannelHealth(workflowId, options = {}) {
  ensureWorkflowId(workflowId);
  const query = new URLSearchParams();
  query.set("workflowId", workflowId);
  if (options.includeMetrics !== false) {
    query.set("includeMetrics", "true");
  }
  const response = await requestJson(
    `/api/channels/telegram/health?${query.toString()}`,
    { method: "GET" }
  );
  return response ?? null;
}

export async function sendChannelTest(payload = {}) {
  ensureWorkflowId(payload.workflowId);
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
  return response ?? null;
}
