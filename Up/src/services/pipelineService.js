import {
  composeSystemPromptFromActions,
  serializeActionsForApi,
} from "../utils/nodeActions";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sanitizeName = (name) => (name || "").trim();
const sanitizePrompt = (prompt) => (prompt || "").trim();
const asBoolean = (value) => Boolean(value);

const buildSystemPrompt = (actions, fallback) => {
  const serialized = composeSystemPromptFromActions(actions);
  if (serialized) {
    return serialized;
  }
  return sanitizePrompt(fallback);
};

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message = `请求失败: ${response.status}`;
    try {
      const detail = await response.json();
      message =
        detail?.detail?.message ||
        detail?.detail ||
        detail?.error ||
        message;
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }

  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return null;
}

export async function createPipelineNode(payload) {
  const name = sanitizeName(payload?.name);
  if (!name) {
    throw new Error("节点名称不能为空");
  }
  const actions = serializeActionsForApi(payload?.actions || []);

  const body = {
    name,
    allowLLM: asBoolean(payload?.allowLLM),
    actions,
    systemPrompt: buildSystemPrompt(actions, payload?.systemPrompt),
    createdAt: payload?.createdAt || new Date().toISOString(),
    pipelineId: payload?.pipelineId ?? null,
    status: payload?.status || "draft",
    strategy: payload?.strategy ?? {},
  };

  return request("/api/pipeline-nodes", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updatePipelineNode(nodeId, payload = {}) {
  if (!nodeId) {
    throw new Error("缺少节点 ID");
  }

  const actions =
    payload.actions !== undefined
      ? serializeActionsForApi(payload.actions || [])
      : undefined;

  const body = {};
  if (payload.name !== undefined) body.name = sanitizeName(payload.name);
  if (payload.allowLLM !== undefined) body.allowLLM = asBoolean(payload.allowLLM);
  if (payload.status !== undefined) body.status = payload.status;
  if (payload.pipelineId !== undefined)
    body.pipelineId = payload.pipelineId ?? null;
  if (payload.strategy !== undefined) body.strategy = payload.strategy ?? {};
  if (actions !== undefined) {
    body.actions = actions;
    body.systemPrompt = buildSystemPrompt(actions, payload.systemPrompt);
  } else if (payload.systemPrompt !== undefined) {
    body.systemPrompt = sanitizePrompt(payload.systemPrompt);
  }

  return request(`/api/pipeline-nodes/${encodeURIComponent(nodeId)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function listPipelineNodes(params = {}) {
  const query = new URLSearchParams();
  if (params.pipelineId) query.set("pipelineId", params.pipelineId);
  if (params.status) query.set("status", params.status);
  query.set("page", params.page?.toString() || "1");
  query.set("pageSize", params.pageSize?.toString() || "20");

  const search = query.toString();
  const path = `/api/pipeline-nodes${search ? `?${search}` : ""}`;
  return request(path, { method: "GET" });
}

export async function deletePipelineNode(nodeId) {
  if (!nodeId) {
    throw new Error("缺少节点 ID");
  }
  return request(`/api/pipeline-nodes/${encodeURIComponent(nodeId)}`, {
    method: "DELETE",
  });
}
