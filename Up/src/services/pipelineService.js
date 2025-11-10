import { requestJson } from "./httpClient";
import { composeSystemPromptFromActions } from "../utils/nodeActions";

const sanitizeName = (name) => (name || "").trim();
const sanitizePrompt = (prompt) => (prompt || "").trim();
const asBoolean = (value) => Boolean(value);
const ALLOWED_STATUS = new Set(["draft", "published"]);

const ensureIsoDateTime = (input) => {
  if (input instanceof Date && !Number.isNaN(input.valueOf())) {
    return input.toISOString();
  }
  if (typeof input === "string" && input.trim()) {
    const parsed = Date.parse(input);
    if (!Number.isNaN(parsed)) {
      return new Date(parsed).toISOString();
    }
  }
  return new Date().toISOString();
};

const normalizeStatus = (status) => {
  const value = (status || "").trim().toLowerCase();
  return ALLOWED_STATUS.has(value) ? value : "draft";
};

const sanitizePipelineId = (value) => {
  if (value === undefined) return undefined;
  if (value === null) return null;
  const stringified = String(value ?? "").trim();
  return stringified.length ? stringified : null;
};

const isPlainObject = (candidate) =>
  candidate !== null &&
  typeof candidate === "object" &&
  Object.prototype.toString.call(candidate) === "[object Object]";

const buildSystemPrompt = (actions, fallback) => {
  const serialized = composeSystemPromptFromActions(actions);
  if (serialized) {
    return serialized;
  }
  return sanitizePrompt(fallback);
};

const resolveSystemPrompt = (payload) => {
  const actions = Array.isArray(payload?.actions) ? payload.actions : undefined;
  const fallbackPrompt = payload?.systemPrompt;
  if (actions !== undefined) {
    return buildSystemPrompt(actions, fallbackPrompt);
  }
  if (fallbackPrompt !== undefined) {
    return sanitizePrompt(fallbackPrompt);
  }
  return undefined;
};

export async function createPipelineNode(payload) {
  const name = sanitizeName(payload?.name);
  if (!name) {
    throw new Error("节点名称不能为空");
  }

  const body = {
    name,
    allowLLM: asBoolean(payload?.allowLLM),
    systemPrompt: resolveSystemPrompt(payload) ?? "",
    createdAt: ensureIsoDateTime(payload?.createdAt),
    pipelineId: sanitizePipelineId(payload?.pipelineId) ?? null,
    status: normalizeStatus(payload?.status),
    strategy: isPlainObject(payload?.strategy) ? payload.strategy : {},
  };

  const response = await requestJson("/api/pipeline-nodes", {
    method: "POST",
    body: JSON.stringify(body),
  });

  return response?.data ?? null;
}

export async function updatePipelineNode(nodeId, payload = {}) {
  if (!nodeId) {
    throw new Error("缺少节点 ID");
  }

  const body = {};
  if (payload.name !== undefined) {
    const trimmedName = sanitizeName(payload.name);
    if (!trimmedName) {
      throw new Error("节点名称不能为空");
    }
    body.name = trimmedName;
  }
  if (payload.allowLLM !== undefined) {
    body.allowLLM = asBoolean(payload.allowLLM);
  }
  if (payload.status !== undefined) {
    body.status = normalizeStatus(payload.status);
  }
  if (payload.pipelineId !== undefined) {
    const sanitized = sanitizePipelineId(payload.pipelineId);
    body.pipelineId = sanitized === undefined ? null : sanitized;
  }
  if (payload.strategy !== undefined) {
    body.strategy = isPlainObject(payload.strategy) ? payload.strategy : {};
  }
  const systemPrompt = resolveSystemPrompt(payload);
  if (systemPrompt !== undefined) {
    body.systemPrompt = systemPrompt;
  }

  const response = await requestJson(
    `/api/pipeline-nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "PUT",
      body: JSON.stringify(body),
    }
  );

  return response?.data ?? null;
}

export async function listPipelineNodes(params = {}) {
  const query = new URLSearchParams();
  if (params.pipelineId) query.set("pipelineId", params.pipelineId);
  if (params.status) query.set("status", params.status);
  query.set("page", params.page?.toString() || "1");
  query.set("pageSize", params.pageSize?.toString() || "20");

  const search = query.toString();
  const path = `/api/pipeline-nodes${search ? `?${search}` : ""}`;
  const response = await requestJson(path, { method: "GET" });
  return {
    data: response?.data ?? null,
    meta: response?.meta ?? null,
  };
}

export async function deletePipelineNode(nodeId) {
  if (!nodeId) {
    throw new Error("缺少节点 ID");
  }
  const response = await requestJson(
    `/api/pipeline-nodes/${encodeURIComponent(nodeId)}`,
    {
      method: "DELETE",
    }
  );
  return response?.meta ?? null;
}
