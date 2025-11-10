import { requestJson } from "./httpClient";

const normalizeWorkflowEntity = (data) => {
  if (!data) return data;
  const id = data.id || data.workflowId || null;
  return {
    ...data,
    id,
  };
};

const sanitizeWorkflowPayload = (payload = {}) => {
  const nodeSequence = Array.isArray(payload.nodeSequence)
    ? payload.nodeSequence.filter(Boolean)
    : [];
  if (!nodeSequence.length) {
    throw new Error("WORKFLOW_NODE_REQUIRED");
  }

  const promptBindings = Array.isArray(payload.promptBindings)
    ? payload.promptBindings
        .filter((item) => item?.nodeId && nodeSequence.includes(item.nodeId))
        .map((item) => ({
          nodeId: item.nodeId,
          promptId: item?.promptId || null,
        }))
    : [];

  const normalized = {
    name: payload.name?.trim() || "",
    status: payload.status,
    nodeSequence,
    promptBindings,
    strategy: {
      retryLimit: Number.isFinite(payload.strategy?.retryLimit)
        ? payload.strategy.retryLimit
        : 0,
      timeoutMs: Number.isFinite(payload.strategy?.timeoutMs)
        ? payload.strategy.timeoutMs
        : 0,
    },
    metadata: {
      description: payload.metadata?.description || "",
      tags: Array.isArray(payload.metadata?.tags)
        ? payload.metadata.tags
        : [],
    },
  };
  return normalized;
};

export async function listWorkflows(params = {}) {
  const query = new URLSearchParams();
  if (params.search) {
    query.set("search", params.search);
  }
  if (params.page) {
    query.set("page", params.page);
  }
  if (params.pageSize) {
    query.set("pageSize", params.pageSize);
  }
  const search = query.toString();
  const response = await requestJson(
    `/api/workflows${search ? `?${search}` : ""}`,
    { method: "GET" }
  );
  const items = Array.isArray(response?.data)
    ? response.data.map((item) => normalizeWorkflowEntity(item))
    : [];
  return { items, meta: response?.meta };
}

export async function getWorkflow(workflowId) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const response = await requestJson(`/api/workflows/${workflowId}`, {
    method: "GET",
  });
  return normalizeWorkflowEntity(response?.data || null);
}

export async function createWorkflow(payload = {}) {
  const body = sanitizeWorkflowPayload(payload);
  const response = await requestJson("/api/workflows", {
    method: "POST",
    body: JSON.stringify(body),
  });
  return normalizeWorkflowEntity(response?.data || null);
}

export async function updateWorkflow(workflowId, payload = {}) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const body = sanitizeWorkflowPayload(payload);
  const response = await requestJson(`/api/workflows/${workflowId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
  return normalizeWorkflowEntity(response?.data || null);
}

export async function deleteWorkflow(workflowId) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  await requestJson(`/api/workflows/${workflowId}`, {
    method: "DELETE",
  });
}

export async function publishWorkflow(workflowId, payload = {}) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const response = await requestJson(
    `/api/workflows/${workflowId}/publish`,
    {
      method: "POST",
      body: JSON.stringify({
        notes: payload.notes || "",
      }),
    }
  );
  return normalizeWorkflowEntity(response?.data || null);
}

export async function rollbackWorkflow(workflowId, version) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  if (version === undefined || version === null) {
    throw new Error("缺少回滚版本");
  }
  const response = await requestJson(
    `/api/workflows/${workflowId}/rollback`,
    {
      method: "POST",
      body: JSON.stringify({ version }),
    }
  );
  return normalizeWorkflowEntity(response?.data || null);
}
