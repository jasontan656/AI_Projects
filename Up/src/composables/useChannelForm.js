import { computed, reactive } from "vue";

const TOKEN_REGEX = /^\d{5,}:[A-Za-z0-9_-]{35}$/;

const createDefaultForm = () => ({
  __tokenEditing: false,
  botToken: "",
  maskedBotToken: "",
  webhookUrl: "",
  __webhookBackup: "",
  usePolling: false,
  waitForResult: true,
  workflowMissingMessage: "",
  timeoutMessage: "",
  metadata: {
    allowedChatIds: [],
    rateLimitPerMin: 60,
    locale: "zh-CN",
  },
  security: {
    secret: "",
    certificatePem: "",
    certificateName: "",
  },
});

export function useChannelForm({ onDirtyChange } = {}) {
  const form = reactive(createDefaultForm());
  const baseline = reactive(createDefaultForm());
  const errors = reactive({
    credential: {
      botToken: "",
      webhookUrl: "",
      workflowMissingMessage: "",
      timeoutMessage: "",
    },
    rateLimit: {
      rateLimitPerMin: "",
    },
  });

  const showTokenInput = computed(
    () => !baseline.botToken || form.__tokenEditing,
  );
  const hasMaskedToken = computed(() => Boolean(baseline.maskedBotToken));
  const maskedToken = computed(() =>
    maskToken(baseline.maskedBotToken || baseline.botToken),
  );
  const pollingMode = computed(() => Boolean(form.usePolling));

  function maskToken(token) {
    if (!token) return "尚未设置 Token";
    if (token.length <= 10) return "****";
    return `${token.slice(0, 6)}****${token.slice(-4)}`;
  }

  function resetErrors() {
    errors.credential.botToken = "";
    errors.credential.webhookUrl = "";
    errors.credential.workflowMissingMessage = "";
    errors.credential.timeoutMessage = "";
    errors.rateLimit.rateLimitPerMin = "";
  }

  function copyFromPolicy(policy = {}) {
    form.__tokenEditing = false;
    form.botToken = policy.botToken || policy.maskedBotToken || "";
    form.maskedBotToken = policy.maskedBotToken || "";
    form.webhookUrl = policy.webhookUrl || "";
    form.__webhookBackup = policy.webhookUrl || "";
    form.usePolling = Boolean(policy.usePolling);
    form.waitForResult = Boolean(policy.waitForResult ?? true);
    form.workflowMissingMessage = policy.workflowMissingMessage || "";
    form.timeoutMessage = policy.timeoutMessage || "";
    form.metadata = {
      allowedChatIds: Array.isArray(policy.metadata?.allowedChatIds)
        ? [...policy.metadata.allowedChatIds]
        : [],
      rateLimitPerMin: Number.isFinite(policy.metadata?.rateLimitPerMin)
        ? policy.metadata.rateLimitPerMin
        : 60,
      locale: policy.metadata?.locale || "zh-CN",
    };
    form.security = {
      secret: policy.security?.secret || "",
      certificatePem: policy.security?.certificatePem || "",
      certificateName: policy.security?.certificateName || "",
    };
  }

  function resetBaseline() {
    baseline.botToken = form.botToken;
    baseline.maskedBotToken = form.maskedBotToken;
    baseline.webhookUrl = form.webhookUrl;
    baseline.__webhookBackup = form.__webhookBackup;
    baseline.usePolling = form.usePolling;
    baseline.waitForResult = form.waitForResult;
    baseline.workflowMissingMessage = form.workflowMissingMessage;
    baseline.timeoutMessage = form.timeoutMessage;
    baseline.metadata = {
      allowedChatIds: [...form.metadata.allowedChatIds],
      rateLimitPerMin: form.metadata.rateLimitPerMin,
      locale: form.metadata.locale,
    };
    baseline.security = {
      secret: form.security.secret,
      certificatePem: form.security.certificatePem,
      certificateName: form.security.certificateName,
    };
  }

  function enableTokenEdit() {
    form.__tokenEditing = true;
    form.botToken = "";
    emitDirty();
  }

  function cancelTokenEdit() {
    form.__tokenEditing = false;
    form.botToken = baseline.botToken;
    emitDirty();
  }

  function handlePollingToggle() {
    form.usePolling = !form.usePolling;
    if (form.usePolling) {
      form.__webhookBackup = form.webhookUrl || form.__webhookBackup || "";
      form.webhookUrl = "";
    } else if (!form.webhookUrl && form.__webhookBackup) {
      form.webhookUrl = form.__webhookBackup;
    }
    emitDirty();
  }

  function validate() {
    resetErrors();
    if (showTokenInput.value && !TOKEN_REGEX.test(form.botToken)) {
      errors.credential.botToken = "Token 格式不正确";
    }
    if (!form.usePolling) {
      if (!form.webhookUrl || !form.webhookUrl.startsWith("https://")) {
        errors.credential.webhookUrl = "Webhook 必须为 https 地址";
      }
    }
    if (form.workflowMissingMessage.length > 256) {
      errors.credential.workflowMissingMessage = "长度不可超过 256 字";
    }
    if (form.timeoutMessage.length > 256) {
      errors.credential.timeoutMessage = "长度不可超过 256 字";
    }
    if (
      form.metadata.rateLimitPerMin < 1 ||
      form.metadata.rateLimitPerMin > 600
    ) {
      errors.rateLimit.rateLimitPerMin = "范围 1~600";
    }
    return (
      !errors.credential.botToken &&
      !errors.credential.webhookUrl &&
      !errors.credential.workflowMissingMessage &&
      !errors.credential.timeoutMessage &&
      !errors.rateLimit.rateLimitPerMin
    );
  }

  function buildPayload() {
    const credential = {
      usePolling: Boolean(form.usePolling),
      waitForResult: form.waitForResult,
      workflowMissingMessage: form.workflowMissingMessage,
      timeoutMessage: form.timeoutMessage,
      webhookUrl: form.usePolling ? "" : form.webhookUrl,
    };
    if (showTokenInput.value && form.botToken) {
      credential.botToken = form.botToken;
    }

  const rateLimit = {
    allowedChatIds: form.metadata.allowedChatIds
      .map((id) => id.trim())
      .filter((id) => id.length > 0),
    rateLimitPerMin: form.metadata.rateLimitPerMin,
    locale: form.metadata.locale,
  };

    const security = {
      secret: form.security.secret || "",
      certificatePem: form.security.certificatePem || "",
      certificateName: form.security.certificateName || "",
    };

    return {
      credential,
      rateLimit,
      security,
    };
  }

  function isDirty() {
    if (showTokenInput.value && form.botToken !== baseline.botToken) return true;
    if (form.webhookUrl !== baseline.webhookUrl) return true;
    if (form.usePolling !== baseline.usePolling) return true;
    if (form.waitForResult !== baseline.waitForResult) return true;
    if (form.workflowMissingMessage !== baseline.workflowMissingMessage) {
      return true;
    }
    if (form.timeoutMessage !== baseline.timeoutMessage) return true;
    if (form.metadata.rateLimitPerMin !== baseline.metadata.rateLimitPerMin) {
      return true;
    }
    if (form.metadata.locale !== baseline.metadata.locale) return true;
    if (
      form.metadata.allowedChatIds.length !==
      baseline.metadata.allowedChatIds.length
    ) {
      return true;
    }
    for (let i = 0; i < form.metadata.allowedChatIds.length; i += 1) {
      if (
        form.metadata.allowedChatIds[i] !==
        baseline.metadata.allowedChatIds[i]
      ) {
        return true;
      }
    }
    if (form.security.secret !== baseline.security.secret) return true;
    if (form.security.certificatePem !== baseline.security.certificatePem) {
      return true;
    }
    return false;
  }

  function emitDirty() {
    if (typeof onDirtyChange === "function") {
      onDirtyChange(isDirty());
    }
  }

  return {
    form,
    baseline,
    errors,
    showTokenInput,
    hasMaskedToken,
    maskedToken,
    pollingMode,
    copyFromPolicy,
    resetBaseline,
    enableTokenEdit,
    cancelTokenEdit,
    handlePollingToggle,
    validate,
    buildPayload,
    maskToken,
    isDirty,
    emitDirty,
  };
}
