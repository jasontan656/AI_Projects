import { createWorkflowLogStream } from "./pipelineSseClient";

const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function subscribeWorkflowLogs(
  workflowId,
  { onMessage, onError, onRetry, heartbeatMs } = {}
) {
  const stream = createWorkflowLogStream(
    workflowId,
    {
      onMessage,
      onError,
      onRetry,
    },
    { heartbeatMs }
  );
  stream.start();
  return () => stream.stop();
}

export async function fetchWorkflowLogs(workflowId, params = {}) {
  if (!workflowId) {
    throw new Error("缺少 workflowId");
  }
  const query = new URLSearchParams();
  if (params.limit) query.set("limit", params.limit);
  if (params.level) query.set("level", params.level);
  if (params.nodeId) query.set("nodeId", params.nodeId);
  const response = await fetch(
    `${baseUrl}/api/workflows/${workflowId}/logs?${query.toString()}`
  );
  if (!response.ok) {
    throw new Error(`导出失败: ${response.status}`);
  }
  return response.json();
}
