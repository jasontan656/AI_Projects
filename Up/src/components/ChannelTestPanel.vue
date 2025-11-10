<template>
  <section class="test-panel">
    <header>
      <div>
        <h3>发送测试消息</h3>
        <p>用于验证 Telegram Bot 是否可用（1 分钟至多 3 次）。</p>
      </div>
    </header>
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
      <el-empty v-if="!history.length" description="暂无测试记录" />
      <ul v-else>
        <li v-for="item in history" :key="item.timestamp" :class="['test-panel__history-item', `is-${item.status || 'unknown'}`]">
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
import { computed, onBeforeUnmount, reactive, watch } from "vue";

const props = defineProps({
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

onBeforeUnmount(() => {
  if (timer) {
    cancelAnimationFrame(timer);
    timer = null;
  }
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
