import { requestJson } from "./httpClient";

export async function listWorkflowVariables(workflowId) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const response = await requestJson(
    `/api/workflows/${workflowId}/variables`,
    { method: "GET" }
  );
  return response?.data || [];
}

export async function listWorkflowTools(workflowId) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const response = await requestJson(
    `/api/workflows/${workflowId}/tools`,
    { method: "GET" }
  );
  return response?.data || [];
}
