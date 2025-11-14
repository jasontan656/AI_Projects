<template>
  <ChannelFormShell
    :published="published"
    title="Telegram 渠道配置"
    subtitle="配置 Bot Token、Webhook 与安全策略。"
    @go-publish="$emit('go-publish')"
  >
    <template #actions>
      <ChannelSubmitActions
        :saving="saving"
        :unbinding="unbinding"
        :disabled="saveButtonDisabled"
        :has-existing-binding="hasExistingBinding"
        :save-disabled-reason="coverageDisabledReason"
        @save="handleSave"
        @unbind="handleUnbind"
      />
    </template>
    <template #coverage>
      <ChannelCoverageGate
        :coverage="coverage"
        :loading="coverageLoading"
        :error="coverageAlertMessage"
        @run-tests="handleRunCoverageTests"
      />
    </template>

    <el-form label-position="top" class="channel-form__body" :disabled="disabled">
      <ChannelCredentialCard
        :form="form"
        :errors="errors.credential"
        :show-token-input="showTokenInput"
        :has-masked-token="hasMaskedToken"
        :masked-token="maskedToken"
        :polling-mode="pollingMode"
        :show-webhook-warning="showWebhookWarning"
        @enable-token-edit="enableTokenEdit"
        @cancel-token-edit="cancelTokenEdit"
        @toggle-polling="handlePollingToggle"
      />

      <ChannelRateLimitForm
        :metadata="form.metadata"
        :errors="errors.rateLimit"
      />

      <section class="channel-form__variables">
        <p>可用变量：<code>{workflow_id}</code>、<code>{correlation_id}</code></p>
      </section>

      <ChannelSecurityPanel
        :security="form.security"
        :validation-result="securitySnapshot"
        :validating="securityValidating"
        :validation-error="securityError"
        :disabled="disabled"
        @validate="handleValidateSecurity"
        @update:secret="(value) => (form.security.secret = value)"
        @update:certificate="(value) => (form.security.certificatePem = value)"
        @update:certificate-name="(value) => (form.security.certificateName = value)"
      />
    </el-form>
  </ChannelFormShell>
</template>

<script setup>
import { computed, watch } from "vue";

import { useChannelForm } from "@up/composables/useChannelForm.js";

import ChannelFormShell from "./channel-form/ChannelFormShell.vue";
import ChannelCoverageGate from "./channel-form/ChannelCoverageGate.vue";
import ChannelSubmitActions from "./channel-form/ChannelSubmitActions.vue";
import ChannelCredentialCard from "./channel-form/ChannelCredentialCard.vue";
import ChannelRateLimitForm from "./channel-form/ChannelRateLimitForm.vue";
import ChannelSecurityPanel from "./channel-form/ChannelSecurityPanel.vue";

const props = defineProps({
  policy: {
    type: Object,
    default: () => ({}),
  },
  saving: {
    type: Boolean,
    default: false,
  },
  unbinding: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  published: {
    type: Boolean,
    default: false,
  },
  coverage: {
    type: Object,
    default: () => null,
  },
  coverageLoading: {
    type: Boolean,
    default: false,
  },
  coverageError: {
    type: String,
    default: "",
  },
  securitySnapshot: {
    type: Object,
    default: () => null,
  },
  securityValidating: {
    type: Boolean,
    default: false,
  },
  securityError: {
    type: String,
    default: "",
  },
  securityBlockingMessage: {
    type: String,
    default: "",
  },
});

const emit = defineEmits([
  "save",
  "dirty-change",
  "unbind",
  "go-publish",
  "run-coverage-tests",
  "validate-security",
]);

const whitelist = (import.meta.env.VITE_TELEGRAM_WEBHOOK_WHITELIST || "")
  .split(",")
  .map((item) => item.trim())
  .filter(Boolean);

const {
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
  isDirty,
  emitDirty,
} = useChannelForm({
  onDirtyChange: (dirty) => emit("dirty-change", dirty),
});

const hasExistingBinding = computed(
  () => Boolean(baseline.botToken || baseline.webhookUrl),
);

const showWebhookWarning = computed(() => {
  if (pollingMode.value) return false;
  if (!whitelist.length || !form.webhookUrl) return false;
  try {
    const url = new URL(form.webhookUrl);
    return !whitelist.includes(url.hostname);
  } catch {
    return false;
  }
});

const coverage = computed(() => {
  if (!props.coverage) return null;
  return {
    ...props.coverage,
    mode: pollingMode.value ? "polling" : props.coverage.mode || "webhook",
  };
});

const coverageAllowsSave = computed(
  () => pollingMode.value || coverage.value?.status === "green",
);

const coverageDisabledReason = computed(() => {
  if (pollingMode.value) {
    return "Polling 模式下需按操作手册手动验证，保存后不会记录到覆盖测试。";
  }
  return coverageAllowsSave.value ? "" : "覆盖测试未通过，无法保存渠道配置";
});

const coverageAlertMessage = computed(
  () => props.coverageError || props.securityBlockingMessage || "",
);

const securitySnapshot = computed(() => props.securitySnapshot || null);
const securityValidating = computed(() => props.securityValidating);
const securityError = computed(() => props.securityError);

const saveButtonDisabled = computed(
  () =>
    props.disabled ||
    !validate() ||
    props.coverageLoading ||
    !coverageAllowsSave.value,
);

const handleSave = () => {
  if (!validate()) return;
  const payload = buildPayload();
  emit("save", createRequestBody(payload));
};

const handleUnbind = () => emit("unbind");
const handleRunCoverageTests = () => emit("run-coverage-tests");

const handleValidateSecurity = () => {
  if (pollingMode.value) {
    emit("validate-security", null);
    return;
  }
  const secret = form.security.secret;
  if (!secret) {
    emit("validate-security", null);
    return;
  }
  emit("validate-security", {
    secret,
    certificate: form.security.certificatePem,
    webhookUrl: form.webhookUrl,
  });
};

watch(
  () => props.policy,
  (next) => {
    copyFromPolicy(next || {});
    resetBaseline();
    emitDirty();
  },
  { immediate: true, deep: true },
);

watch(
  () => [
    form.botToken,
    form.webhookUrl,
    form.usePolling,
    form.waitForResult,
    form.workflowMissingMessage,
    form.timeoutMessage,
    form.metadata.allowedChatIds,
    form.metadata.rateLimitPerMin,
    form.metadata.locale,
    form.__tokenEditing,
    form.security.secret,
    form.security.certificatePem,
    form.security.certificateName,
  ],
  () => emitDirty(),
  { deep: true },
);

defineExpose({
  isDirty,
});

function createRequestBody(payload) {
  const body = {
    credential: payload.credential,
    rateLimit: payload.rateLimit,
    security: payload.security,
  };
  // Legacy fields kept for backward compatibility while backend migrates.
  body.usePolling = payload.credential.usePolling;
  body.waitForResult = payload.credential.waitForResult;
  body.workflowMissingMessage = payload.credential.workflowMissingMessage;
  body.timeoutMessage = payload.credential.timeoutMessage;
  body.webhookUrl = payload.credential.webhookUrl;
  body.metadata = payload.rateLimit;
  if (payload.credential.botToken) {
    body.botToken = payload.credential.botToken;
  }
  if (payload.security.secret) {
    body.webhookSecret = payload.security.secret;
  }
  if (payload.security.certificatePem) {
    body.certificatePem = payload.security.certificatePem;
  }
  return body;
}
</script>

<style scoped>
.channel-form__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.channel-form__variables {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
</style>
