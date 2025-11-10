<template>
  <section class="channel-form" v-if="published">
    <header class="channel-form__header">
      <div>
        <h3>Telegram 渠道配置</h3>
        <p>配置 Bot Token、Webhook 与回退文案。</p>
      </div>
      <div class="channel-form__actions">
        <el-button
          text
          :disabled="saving || disabled || !hasExistingBinding"
          @click="handleUnbind"
          :loading="unbinding"
        >
          解绑渠道
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          :disabled="disabled || !canSave"
          @click="handleSave"
        >
          保存配置
        </el-button>
      </div>
    </header>
    <el-form label-position="top" class="channel-form__body" :disabled="disabled">
      <el-form-item label="Bot Token" :error="errors.botToken">
        <template v-if="showTokenInput">
          <el-input
            v-model.trim="form.botToken"
            type="password"
            show-password
            placeholder="请输入 Bot Token"
          />
          <el-button text size="small" v-if="hasMaskedToken" @click="cancelTokenEdit">
            保留原 Token
          </el-button>
        </template>
        <template v-else>
          <div class="channel-form__token-mask">
            <span>{{ maskedToken }}</span>
            <el-button text size="small" @click="enableTokenEdit">重新输入 Token</el-button>
          </div>
        </template>
      </el-form-item>

      <el-form-item label="Webhook URL" :error="errors.webhookUrl">
        <el-input v-model.trim="form.webhookUrl" placeholder="https://example.com/telegram" />
        <p v-if="showWebhookWarning" class="channel-form__warning">
          当前域名未在白名单中，保存后请确认入口代理允许该地址。
        </p>
      </el-form-item>

      <el-form-item label="等待节点结果">
        <el-switch v-model="form.waitForResult" />
      </el-form-item>

      <el-form-item label="Workflow 缺失提示（支持 {workflow_id}）" :error="errors.workflowMissingMessage">
        <el-input
          v-model="form.workflowMissingMessage"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 3 }"
        />
      </el-form-item>

      <el-form-item label="超时提示（支持 {correlation_id}）" :error="errors.timeoutMessage">
        <el-input
          v-model="form.timeoutMessage"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 3 }"
        />
      </el-form-item>

      <section class="channel-form__meta">
        <div class="channel-form__meta-field">
          <label>允许的 chatId</label>
          <el-select
            v-model="form.metadata.allowedChatIds"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入 chatId 回车添加"
          />
          <p class="channel-form__hint">留空表示不限；建议填生产群/用户 chatId。</p>
        </div>
        <div class="channel-form__meta-field">
          <label>速率限制（次/分钟）</label>
          <el-input-number
            v-model="form.metadata.rateLimitPerMin"
            :min="1"
            :max="600"
          />
        </div>
        <div class="channel-form__meta-field">
          <label>Locale</label>
          <el-select v-model="form.metadata.locale">
            <el-option label="中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </div>
      </section>

      <section class="channel-form__variables">
        <p>可用变量：<code>{workflow_id}</code>、<code>{correlation_id}</code></p>
      </section>
    </el-form>
  </section>
  <section v-else class="channel-form__placeholder">
    <el-empty description="请先发布 Workflow 才能绑定 Telegram 渠道">
      <el-button type="primary" @click="$emit('go-publish')">前往发布</el-button>
    </el-empty>
  </section>
</template>

<script setup>
import { computed, reactive, watch } from "vue";

const TOKEN_REGEX = /^\d{5,}:[A-Za-z0-9_-]{35}$/;

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
});

const emit = defineEmits(["save", "dirty-change", "unbind", "go-publish"]);

const form = reactive(createForm());
const baseline = reactive(createForm());
const errors = reactive({
  botToken: "",
  webhookUrl: "",
  workflowMissingMessage: "",
  timeoutMessage: "",
});

const showTokenInput = computed(() => !baseline.botToken || form.__tokenEditing);
const hasMaskedToken = computed(() => Boolean(baseline.maskedBotToken));
const maskedToken = computed(() =>
  maskToken(baseline.maskedBotToken || baseline.botToken)
);
const hasExistingBinding = computed(() => Boolean(baseline.botToken || baseline.webhookUrl));

const showWebhookWarning = computed(() => {
  const whitelist = (import.meta.env.VITE_TELEGRAM_WEBHOOK_WHITELIST || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (!whitelist.length || !form.webhookUrl) return false;
  try {
    const url = new URL(form.webhookUrl);
    return !whitelist.includes(url.hostname);
  } catch {
    return false;
  }
});

function createForm() {
  return {
    __tokenEditing: false,
    botToken: "",
    maskedBotToken: "",
    webhookUrl: "",
    waitForResult: true,
    workflowMissingMessage: "",
    timeoutMessage: "",
    metadata: {
      allowedChatIds: [],
      rateLimitPerMin: 60,
      locale: "zh-CN",
    },
  };
}

const extractDisplayToken = (source = {}) =>
  source.botToken || source.maskedBotToken || "";

const copyIntoForm = (source = {}) => {
  form.__tokenEditing = false;
  form.botToken = extractDisplayToken(source);
  form.maskedBotToken = source.maskedBotToken || "";
  form.webhookUrl = source.webhookUrl || "";
  form.waitForResult = Boolean(source.waitForResult ?? true);
  form.workflowMissingMessage = source.workflowMissingMessage || "";
  form.timeoutMessage = source.timeoutMessage || "";
  form.metadata = {
    allowedChatIds: Array.isArray(source.metadata?.allowedChatIds)
      ? [...source.metadata.allowedChatIds]
      : [],
    rateLimitPerMin: source.metadata?.rateLimitPerMin ?? 60,
    locale: source.metadata?.locale || "zh-CN",
  };
};

const resetBaseline = () => {
  baseline.botToken = form.botToken;
  baseline.maskedBotToken = form.maskedBotToken;
  baseline.webhookUrl = form.webhookUrl;
  baseline.waitForResult = form.waitForResult;
  baseline.workflowMissingMessage = form.workflowMissingMessage;
  baseline.timeoutMessage = form.timeoutMessage;
  baseline.metadata = {
    allowedChatIds: [...form.metadata.allowedChatIds],
    rateLimitPerMin: form.metadata.rateLimitPerMin,
    locale: form.metadata.locale,
  };
};

const enableTokenEdit = () => {
  form.__tokenEditing = true;
  form.botToken = "";
};

const cancelTokenEdit = () => {
  form.__tokenEditing = false;
  form.botToken = baseline.botToken;
  emitDirty();
};

const validate = () => {
  errors.botToken = "";
  errors.webhookUrl = "";
  errors.workflowMissingMessage = "";
  errors.timeoutMessage = "";
  if (showTokenInput.value && !TOKEN_REGEX.test(form.botToken)) {
    errors.botToken = "Token 格式不正确";
  }
  if (!form.webhookUrl || !form.webhookUrl.startsWith("https://")) {
    errors.webhookUrl = "Webhook 必须为 https 地址";
  }
  if (form.workflowMissingMessage.length > 256) {
    errors.workflowMissingMessage = "长度不可超过 256 字";
  }
  if (form.timeoutMessage.length > 256) {
    errors.timeoutMessage = "长度不可超过 256 字";
  }
  if (
    form.metadata.rateLimitPerMin < 1 ||
    form.metadata.rateLimitPerMin > 600
  ) {
    return false;
  }
  return (
    !errors.botToken &&
    !errors.webhookUrl &&
    !errors.workflowMissingMessage &&
    !errors.timeoutMessage
  );
};

const canSave = computed(() => validate());

const handleSave = () => {
  if (!validate()) return;
  const payload = {
    webhookUrl: form.webhookUrl,
    waitForResult: form.waitForResult,
    workflowMissingMessage: form.workflowMissingMessage,
    timeoutMessage: form.timeoutMessage,
    metadata: {
      allowedChatIds: form.metadata.allowedChatIds.map((id) => id.trim()),
      rateLimitPerMin: form.metadata.rateLimitPerMin,
      locale: form.metadata.locale,
    },
  };

  if (showTokenInput.value && form.botToken) {
    payload.botToken = form.botToken;
  }

  emit("save", payload);
};

const handleUnbind = () => {
  emit("unbind");
};

const maskToken = (token) => {
  if (!token) return "尚未设置 Token";
  if (token.length <= 10) return "****";
  return `${token.slice(0, 6)}****${token.slice(-4)}`;
};

const emitDirty = () => {
  emit("dirty-change", isDirty());
};

const isDirty = () => {
  if (showTokenInput.value && form.botToken !== baseline.botToken) return true;
  if (form.webhookUrl !== baseline.webhookUrl) return true;
  if (form.waitForResult !== baseline.waitForResult) return true;
  if (form.workflowMissingMessage !== baseline.workflowMissingMessage) return true;
  if (form.timeoutMessage !== baseline.timeoutMessage) return true;
  if (form.metadata.rateLimitPerMin !== baseline.metadata.rateLimitPerMin) return true;
  if (form.metadata.locale !== baseline.metadata.locale) return true;
  if (
    form.metadata.allowedChatIds.length !== baseline.metadata.allowedChatIds.length
  ) {
    return true;
  }
  for (let i = 0; i < form.metadata.allowedChatIds.length; i += 1) {
    if (form.metadata.allowedChatIds[i] !== baseline.metadata.allowedChatIds[i]) {
      return true;
    }
  }
  return false;
};

watch(
  () => props.policy,
  (next) => {
    copyIntoForm(next || {});
    resetBaseline();
    emitDirty();
  },
  { immediate: true, deep: true }
);

watch(
  () => [
    form.botToken,
    form.webhookUrl,
    form.waitForResult,
    form.workflowMissingMessage,
    form.timeoutMessage,
    form.metadata.allowedChatIds,
    form.metadata.rateLimitPerMin,
    form.metadata.locale,
    form.__tokenEditing,
  ],
  () => emitDirty(),
  { deep: true }
);

defineExpose({
  isDirty,
});
</script>

<style scoped>
.channel-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.channel-form__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: flex-start;
}

.channel-form__header h3 {
  margin: 0;
}

.channel-form__actions {
  display: flex;
  gap: var(--space-2);
}

.channel-form__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.channel-form__token-mask {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
  width: fit-content;
}

.channel-form__warning {
  margin: var(--space-1) 0 0;
  color: #a45c00;
  font-size: var(--font-size-xs);
}

.channel-form__hint {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.channel-form__meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}

.channel-form__meta-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.channel-form__variables {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.channel-form__placeholder {
  padding: var(--space-5) 0;
}
</style>
