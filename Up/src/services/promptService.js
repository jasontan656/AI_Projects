const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sanitize = (value) => (value || "").trim();

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

export async function listPrompts(params = {}) {
  const query = new URLSearchParams();
  query.set("page", params.page?.toString() || "1");
  query.set("pageSize", params.pageSize?.toString() || "50");
  const search = query.toString();
  return request(`/api/prompts${search ? `?${search}` : ""}`, { method: "GET" });
}

export async function createPrompt(payload) {
  const name = sanitize(payload?.name);
  const markdown = sanitize(payload?.markdown);

  if (!markdown) {
    throw new Error("Markdown 内容不能为空");
  }

  return request("/api/prompts", {
    method: "POST",
    body: JSON.stringify({
      name: name || "未命名提示词",
      markdown,
    }),
  });
}

export async function updatePrompt(promptId, payload = {}) {
  if (!promptId) {
    throw new Error("缺少提示词 ID");
  }
  const body = {};
  if (payload.name !== undefined) body.name = sanitize(payload.name);
  if (payload.markdown !== undefined) body.markdown = sanitize(payload.markdown);

  return request(`/api/prompts/${encodeURIComponent(promptId)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function deletePrompt(promptId) {
  if (!promptId) {
    throw new Error("缺少提示词 ID");
  }
  return request(`/api/prompts/${encodeURIComponent(promptId)}`, {
    method: "DELETE",
  });
}

export const listPromptDrafts = listPrompts;
export const createPromptDraft = createPrompt;
export const updatePromptDraft = updatePrompt;
export const deletePromptDraft = deletePrompt;
