<template>
  <section class="health-card">
    <header>
      <h3>健康状态</h3>
      <div class="health-card__actions">
        <el-button link size="small" :loading="refreshing" @click="$emit('refresh')">
          立即刷新
        </el-button>
      </div>
    </header>
    <div class="health-card__status" :class="statusClass">
      <span class="health-card__dot" :class="statusClass"></span>
      <div>
        <strong>{{ statusLabel }}</strong>
        <p class="health-card__timestamp">
          {{ health?.lastCheckedAt ? formatDate(health.lastCheckedAt) : "尚未检查" }}
        </p>
      </div>
    </div>
    <div class="health-card__metrics" v-if="health?.metrics">
      <div>
        <p class="health-card__metric-label">Webhook 延迟</p>
        <p class="health-card__metric-value">
          {{ health.metrics.webhookLatencyMs ?? "--" }} ms
        </p>
      </div>
      <div>
        <p class="health-card__metric-label">队列积压</p>
        <p class="health-card__metric-value">
          {{ health.metrics.queueBacklog ?? "--" }}
        </p>
      </div>
      <div>
        <p class="health-card__metric-label">Worker 心跳</p>
        <p class="health-card__metric-value">
          {{ health.metrics.workerHeartbeatSec ?? "--" }} s
        </p>
      </div>
    </div>
    <p v-if="health?.lastError" class="health-card__error">
      {{ health.lastError }}
      <el-button
        v-if="health.traceId"
        text
        size="small"
        @click="$emit('copy-trace', health.traceId)"
      >
        复制 TraceId
      </el-button>
    </p>
    <p v-if="paused" class="health-card__paused">
      已暂停轮询，请检查网络或点击上方“立即刷新”恢复。
    </p>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  health: {
    type: Object,
    default: () => null,
  },
  refreshing: {
    type: Boolean,
    default: false,
  },
  paused: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["refresh", "copy-trace"]);

const statusLabelMap = {
  up: "正常",
  degraded: "性能下降",
  down: "异常",
  unknown: "未知",
};

const statusClass = computed(() => `is-${props.health?.status || "unknown"}`);
const statusLabel = computed(
  () => statusLabelMap[props.health?.status] || "未知"
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
.health-card {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.health-card header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.health-card__status {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border-radius: var(--radius-sm);
  background: rgba(148, 163, 184, 0.12);
}

.health-card__dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.health-card__dot.is-up {
  background: #12b76a;
}

.health-card__dot.is-degraded {
  background: #f79009;
}

.health-card__dot.is-down {
  background: #f04438;
}

.health-card__dot.is-unknown {
  background: #94a3b8;
}

.health-card__timestamp {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.health-card__metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--space-2);
}

.health-card__metric-label {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.health-card__metric-value {
  margin: 0;
  font-size: var(--font-size-md);
  font-weight: 600;
}

.health-card__error {
  margin: 0;
  font-size: var(--font-size-xs);
  color: #f04438;
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.health-card__paused {
  margin: 0;
  font-size: var(--font-size-xs);
  color: #a45c00;
}
</style>
