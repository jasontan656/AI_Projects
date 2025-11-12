import { requestJson } from "./httpClient";
import {
  buildWorkflowPayload,
  normalizeWorkflowEntity,
} from "../schemas/workflowDraft";

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
  const body = buildWorkflowPayload(payload);
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
  const body = buildWorkflowPayload(payload);
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
