const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const resolveActorHeaders = () => {
  if (typeof window === "undefined") {
    return {};
  }

  const actorId =
    window.localStorage?.getItem("up.actorId") ||
    import.meta.env.VITE_API_ACTOR_ID ||
    "dev-actor";

  const roles =
    window.localStorage?.getItem("up.actorRoles") ||
    import.meta.env.VITE_API_ACTOR_ROLES ||
    "";

  const tenant =
    window.localStorage?.getItem("up.tenantId") ||
    import.meta.env.VITE_API_TENANT_ID ||
    "";

  const headers = {};
  if (actorId) {
    headers["X-Actor-Id"] = actorId;
  }
  if (roles) {
    headers["X-Actor-Roles"] = roles;
  }
  if (tenant) {
    headers["X-Tenant-Id"] = tenant;
  }
  return headers;
};

const extractApiErrorMessage = async (response, fallback) => {
  try {
    const detail = await response.json();
    if (detail) {
      const code = detail.code || detail?.detail?.code;
      const message =
        detail.message ||
        detail?.detail?.message ||
        detail?.detail?.[0]?.msg ||
        detail?.error;
      if (code && message) {
        return `${code}: ${message}`;
      }
      if (message) {
        return message;
      }
    }
  } catch {
    // ignore JSON parse errors
  }
  return fallback;
};

export async function requestJson(path, options = {}) {
  const actorHeaders = resolveActorHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...actorHeaders,
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const fallback = `请求失败: ${response.status}`;
    const message = await extractApiErrorMessage(response, fallback);
    throw new Error(message);
  }

  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return null;
}

