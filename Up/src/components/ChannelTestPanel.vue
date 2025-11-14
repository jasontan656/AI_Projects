<template>
  <section class="test-panel">
    <header>
      <div>
        <h3>发送测试消息</h3>
        <p>用于验证 Telegram Bot 是否可用（1 分钟至多 3 次）。</p>
      </div>
    </header>
    <el-alert
      v-if="pollingMode"
      type="info"
      :closable="false"
      show-icon
      class="test-panel__alert"
      title="Polling 模式提示"
    >
      <p class="test-panel__alert-message">
        当前 workflow 通过 Polling 处理，Webhook 停用。请按照手册在 Bot 中发送 /start 并在 2 分钟内确认日志，结果不会记入覆盖测试。
      </p>
    </el-alert>
    <el-alert
      v-if="requiresRetest"
      type="warning"
      :closable="false"
      show-icon
      class="test-panel__alert"
      data-test="test-panel-retest"
      title="Secret/TLS 已更新"
      description="请重新运行覆盖测试确认新凭据后再触发测试消息。"
    />
    <el-form label-position="top" class="test-panel__form" :disabled="disabled">
      <el-form-item label="chatId" :error="errors.chatId">
        <el-input
          v-model.trim="form.chatId"
          placeholder="输入 chatId"
          type="number"
        />
      </el-form-item>
      <el-form-item label="测试内容">
        <el-input
          v-model="form.payloadText"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="/ping workflow_id"
        />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.waitForResult">等待 Workflow 执行结果（最多 15 秒）</el-checkbox>
      </el-form-item>
      <div class="test-panel__actions">
        <el-button
          type="primary"
          :loading="testing"
          :disabled="disabled || !form.chatId || coolingDown"
          @click="handleSend"
        >
          {{ coolingDown ? `请稍后 (${cooldownSeconds}s)` : "发送测试" }}
        </el-button>
      </div>
    </el-form>

    <section class="test-panel__history">
      <header>
        <h4>最近记录</h4>
      </header>
      <el-empty v-if="!historyItems.length" description="暂无测试记录" />
      <ul v-else>
        <li v-for="item in historyItems" :key="item.timestamp || item.testId || item.message" :class="['test-panel__history-item', `is-${item.status || 'unknown'}`]">
          <div>
            <strong>{{ item.status === "success" ? "成功" : "失败" }}</strong>
            <span class="test-panel__history-meta">
              {{ formatDate(item.timestamp) }} · chatId {{ item.chatId }}
            </span>
          </div>
          <p class="test-panel__history-meta">
            {{ item.message || item.error || item.errorCode || "" }}
            <span v-if="item.responseTimeMs"> · {{ item.responseTimeMs }}ms</span>
          </p>
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";

import { createSseStream } from "../services/pipelineSseClient";

const props = defineProps({
  workflowId: {
    type: String,
    default: "",
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  testing: {
    type: Boolean,
    default: false,
  },
  history: {
    type: Array,
    default: () => [],
  },
  cooldownUntil: {
    type: Number,
    default: 0,
  },
  requiresRetest: {
    type: Boolean,
    default: false,
  },
  pollingMode: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["send-test"]);

const form = reactive({
  chatId: "",
  payloadText: "/ping {workflow_id}",
  waitForResult: false,
});

const errors = reactive({
  chatId: "",
});

const now = reactive({ value: Date.now() });
let timer = null;
let streamHandle = null;
const liveHistory = ref([]);

const normalizeEvent = (event) => {
  if (!event) return null;
  const metadata = event.metadata || {};
  const scenarios = event.scenarios || metadata.scenarios || [];
  const scenarioMessage = scenarios.length ? `场景 ${scenarios.join(", ")}` : "";
  const duration = metadata.durationMs ?? event.responseTimeMs;
  const baseMessage = metadata.message || event.message || metadata.summary || scenarioMessage;
  const fullMessage = duration ? `${baseMessage || "覆盖测试"} · ${duration}ms` : baseMessage;
  return {
    status: event.status || "unknown",
    chatId: metadata.chatId || event.chatId || metadata.botUsername || "-",
    timestamp: event.timestamp || metadata.timestamp,
    message: fullMessage,
    responseTimeMs: duration,
    error: event.lastError || event.error,
    errorCode: metadata.errorCode || event.errorCode,
    testId: metadata.testId || event.lastRunId,
  };
};

const pushEvent = (event) => {
  const normalized = normalizeEvent(event);
  if (!normalized) return;
  liveHistory.value = [normalized, ...liveHistory.value.filter(Boolean)].slice(0, 10);
};

const stopStream = () => {
  if (streamHandle) {
    streamHandle.stop();
    streamHandle = null;
  }
};

const startStream = () => {
  if (!props.workflowId || props.disabled) {
    stopStream();
    return;
  }
  stopStream();
  streamHandle = createSseStream({
    path: `/api/workflows/${props.workflowId}/tests/stream`,
    onMessage: (event) => {
      if (!event || event.workflowId !== props.workflowId) return;
      pushEvent(event);
    },
    onError: () => {
      stopStream();
    },
  });
  streamHandle.start();
};

const coolingDown = computed(() => props.cooldownUntil > now.value);
const cooldownSeconds = computed(() => {
  if (!coolingDown.value) return 0;
  return Math.ceil((props.cooldownUntil - now.value) / 1000);
});

const validate = () => {
  errors.chatId = "";
  if (!form.chatId) {
    errors.chatId = "chatId 不能为空";
    return false;
  }
  return true;
};

const handleSend = () => {
  if (!validate()) return;
  emit("send-test", {
    chatId: form.chatId,
    payloadText: form.payloadText,
    waitForResult: form.waitForResult,
  });
};

const tick = () => {
  now.value = Date.now();
  timer = requestAnimationFrame(tick);
};

watch(
  () => props.cooldownUntil,
  (val) => {
    if (val > Date.now() && !timer) {
      timer = requestAnimationFrame(tick);
    }
    if (val <= Date.now() && timer) {
      cancelAnimationFrame(timer);
      timer = null;
    }
  },
  { immediate: true }
);

watch(
  () => props.workflowId,
  () => {
    liveHistory.value = [];
    startStream();
  },
  { immediate: true }
);

watch(
  () => props.disabled,
  () => {
    startStream();
  }
);

onBeforeUnmount(() => {
  if (timer) {
    cancelAnimationFrame(timer);
    timer = null;
  }
  stopStream();
});

const historyItems = computed(() => {
  const base = [...liveHistory.value, ...(props.history || [])].filter(Boolean);
  if (!base.length) return [];
  const seen = new Set();
  const list = [];
  for (const item of base) {
    const key = [item.timestamp, item.chatId, item.status, item.message].filter(Boolean).join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    list.push(item);
    if (list.length >= 10) break;
  }
  return list;
});

const formatDate = (value) => {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};
</script>

<style scoped>
.test-panel {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.test-panel header h3 {
  margin: 0;
}

.test-panel__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.test-panel__alert {
  margin-bottom: var(--space-2);
}

.test-panel__actions {
  display: flex;
  justify-content: flex-end;
}

.test-panel__history ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 260px;
  overflow-y: auto;
}

.test-panel__history-item {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
}

.test-panel__history-item.is-success {
  border-color: rgba(18, 183, 106, 0.4);
}

.test-panel__history-item.is-failed {
  border-color: rgba(240, 68, 56, 0.4);
}

.test-panel__history-meta {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}
</style>
