import { requestJson } from "./httpClient";

const sanitize = (value) => (value || "").trim();

const ensureValidPageParam = (value, fallback) => {
  const parsed = Number.parseInt(value, 10);
  if (Number.isFinite(parsed) && parsed >= 1 && parsed <= 100) {
    return parsed;
  }
  return fallback;
};

export async function listPrompts(params = {}) {
  const page = ensureValidPageParam(params.page, 1);
  const pageSize = ensureValidPageParam(params.pageSize, 50);

  const query = new URLSearchParams();
  query.set("page", page.toString());
  query.set("pageSize", pageSize.toString());

  const search = query.toString();
  const response = await requestJson(
    `/api/prompts${search ? `?${search}` : ""}`,
    { method: "GET" }
  );
  return {
    data: response?.data ?? null,
    meta: response?.meta ?? null,
  };
}

export async function createPrompt(payload) {
  const name = sanitize(payload?.name);
  const markdown = sanitize(payload?.markdown);

  if (!name) {
    throw new Error("提示词名称不能为空");
  }
  if (!markdown) {
    throw new Error("Markdown 内容不能为空");
  }

  const response = await requestJson("/api/prompts", {
    method: "POST",
    body: JSON.stringify({
      name,
      markdown,
    }),
  });

  return response?.data ?? null;
}

export async function updatePrompt(promptId, payload = {}) {
  if (!promptId) {
    throw new Error("缺少提示词 ID");
  }
  const body = {};
  if (payload.name !== undefined) {
    const trimmed = sanitize(payload.name);
    if (!trimmed) {
      throw new Error("提示词名称不能为空");
    }
    body.name = trimmed;
  }
  if (payload.markdown !== undefined) {
    const trimmedMarkdown = sanitize(payload.markdown);
    if (!trimmedMarkdown) {
      throw new Error("Markdown 内容不能为空");
    }
    body.markdown = trimmedMarkdown;
  }

  if (Object.keys(body).length === 0) {
    throw new Error("缺少可更新的字段");
  }

  const response = await requestJson(
    `/api/prompts/${encodeURIComponent(promptId)}`,
    {
      method: "PUT",
      body: JSON.stringify(body),
    }
  );

  return response?.data ?? null;
}

export async function deletePrompt(promptId) {
  if (!promptId) {
    throw new Error("缺少提示词 ID");
  }
  const response = await requestJson(
    `/api/prompts/${encodeURIComponent(promptId)}`,
    {
      method: "DELETE",
    }
  );
  return response?.meta ?? null;
}

export const listPromptDrafts = listPrompts;
export const createPromptDraft = createPrompt;
export const updatePromptDraft = updatePrompt;
export const deletePromptDraft = deletePrompt;
