import {
  listWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  publishWorkflow,
  rollbackWorkflow,
} from "./workflowService";
import { createWorkflowDraft } from "../schemas/workflowDraft";

export async function fetchWorkflowList(params = {}) {
  const { items, meta } = await listWorkflows(params);
  return {
    items: Array.isArray(items)
      ? items.map((item) => createWorkflowDraft(item))
      : [],
    meta,
  };
}

export async function fetchWorkflowDetail(workflowId) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const entity = await getWorkflow(workflowId);
  return createWorkflowDraft(entity);
}

export async function saveWorkflowDraft(currentWorkflow, payload) {
  if (currentWorkflow?.id) {
    const updated = await updateWorkflow(currentWorkflow.id, payload);
    return createWorkflowDraft(updated);
  }
  const created = await createWorkflow(payload);
  return createWorkflowDraft(created);
}

export async function removeWorkflowDraft(workflowId) {
  if (!workflowId) return;
  await deleteWorkflow(workflowId);
}

export async function publishWorkflowDraft(workflowId, meta = {}) {
  const published = await publishWorkflow(workflowId, meta);
  return createWorkflowDraft(published);
}

export async function rollbackWorkflowDraft(workflowId, version) {
  const rolled = await rollbackWorkflow(workflowId, version);
  return createWorkflowDraft(rolled);
}
