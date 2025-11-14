<template>
  <section class="log-stream">
    <header class="log-stream__header">
      <div>
        <h3>实时日志</h3>
        <p>{{ connectionStatusLabel }}</p>
      </div>
      <div class="log-stream__actions">
        <el-select v-model="filters.level" placeholder="级别" size="small" clearable @change="emitFilter">
          <el-option label="Info" value="info" />
          <el-option label="Warning" value="warning" />
          <el-option label="Error" value="error" />
        </el-select>
        <el-button size="small" @click="togglePause">
          {{ paused ? "恢复" : "暂停" }}
        </el-button>
        <el-button size="small" @click="$emit('export')">导出最近 200 条</el-button>
      </div>
    </header>
    <el-alert
      v-if="!paused && retryIn > 0"
      type="warning"
      :title="retryCountdownLabel"
      :closable="false"
      class="log-stream__alert"
    />
    <div class="log-stream__list" ref="listRef">
      <template v-if="logs.length">
        <article
          v-for="item in logs"
          :key="item.id || item.timestamp"
          :class="['log-stream__item', `is-${item.level || 'info'}`]"
        >
          <div class="log-stream__meta">
            <span class="log-stream__timestamp">{{ formatDate(item.timestamp) }}</span>
            <span class="log-stream__level">{{ (item.level || '').toUpperCase() }}</span>
            <span v-if="item.nodeId" class="log-stream__node">{{ item.nodeId }}</span>
            <span v-if="item.correlationId" class="log-stream__correlation">CID {{ item.correlationId }}</span>
          </div>
          <pre class="log-stream__message">{{ item.message || "" }}</pre>
        </article>
      </template>
      <el-empty v-else description="暂无日志数据" />
    </div>
  </section>
</template>

<script setup>
import { computed, watch, ref } from "vue";

const props = defineProps({
  logs: {
    type: Array,
    default: () => [],
  },
  paused: {
    type: Boolean,
    default: false,
  },
  connected: {
    type: Boolean,
    default: false,
  },
  retryIn: {
    type: Number,
    default: 0,
  },
  retryMessage: {
    type: String,
    default: "",
  },
});

const emit = defineEmits(["toggle", "filter-change", "export"]);

const filters = ref({
  level: "",
});

const retryCountdownLabel = computed(() => {
  if (props.retryIn <= 0) return "";
  if (props.retryMessage) return props.retryMessage;
  const seconds = Math.ceil(props.retryIn / 1000);
  return `日志流已断开，系统将在 ${seconds}s 后重连`;
});

const connectionStatusLabel = computed(() => {
  if (props.paused) return "已暂停";
  if (props.retryIn > 0) return retryCountdownLabel.value;
  return props.connected ? "已连接" : "重连中…";
});

const togglePause = () => {
  emit("toggle");
};

const emitFilter = () => {
  emit("filter-change", { ...filters.value });
};

const listRef = ref(null);

watch(
  () => props.logs.length,
  () => {
    if (props.paused) return;
    requestAnimationFrame(() => {
      const el = listRef.value;
      if (el) {
        el.scrollTop = el.scrollHeight;
      }
    });
  }
);

const formatDate = (value) => {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};
</script>

<style scoped>
.log-stream {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
  padding: var(--space-3);
}

.log-stream__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

.log-stream__actions {
  display: flex;
  gap: var(--space-1);
  align-items: center;
}

.log-stream__alert {
  margin: 0;
}

.log-stream__list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  background: var(--color-bg-muted);
}

.log-stream__item {
  border-radius: var(--radius-xs);
  padding: var(--space-2);
  background: #fff;
  box-shadow: var(--shadow-xs);
}

.log-stream__item.is-error {
  border-left: 4px solid #f04438;
}

.log-stream__item.is-warning {
  border-left: 4px solid #f79009;
}

.log-stream__item.is-info {
  border-left: 4px solid #0ea5e9;
}

.log-stream__meta {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.log-stream__message {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
