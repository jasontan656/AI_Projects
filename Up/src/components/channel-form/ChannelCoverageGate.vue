<template>
  <section class="coverage-gate">
    <div class="coverage-gate__header">
      <div class="coverage-gate__status" :class="statusClass">
        <span class="coverage-gate__dot" :class="statusClass"></span>
        <div>
          <strong>{{ statusLabel }}</strong>
          <p class="coverage-gate__timestamp">
            {{ updatedLabel }}
          </p>
          <p v-if="isPollingMode" class="coverage-gate__mode">Polling 模式 · 覆盖仅供记录</p>
        </div>
      </div>
      <el-button
        text
        size="small"
        :loading="loading"
        @click="$emit('run-tests')"
      >
        重新运行覆盖测试
      </el-button>
    </div>
    <div class="coverage-gate__body">
      <p class="coverage-gate__hint">{{ blockingMessage }}</p>
      <ul v-if="scenarioList.length" class="coverage-gate__scenarios">
        <li v-for="scenario in scenarioList" :key="scenario">
          {{ scenario }}
        </li>
      </ul>
      <p v-if="coverage?.lastError" class="coverage-gate__error">
        {{ coverage.lastError }}
      </p>
      <p v-if="error" class="coverage-gate__error">
        {{ error }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

const STATUS_LABELS = {
  green: "覆盖通过",
  yellow: "需要关注",
  red: "阻塞",
  unknown: "未知",
};

const props = defineProps({
  coverage: {
    type: Object,
    default: () => null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
});

defineEmits(["run-tests"]);

const statusValue = computed(() => props.coverage?.status || "unknown");
const statusClass = computed(() => `is-${statusValue.value}`);
const statusLabel = computed(
  () => STATUS_LABELS[statusValue.value] || STATUS_LABELS.unknown,
);
const isPollingMode = computed(() => props.coverage?.mode === "polling");

const updatedLabel = computed(() => {
  const value = props.coverage?.updatedAt;
  if (!value) {
    return "尚未运行";
  }
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
});

const scenarioList = computed(() =>
  Array.isArray(props.coverage?.scenarios)
    ? props.coverage.scenarios
    : [],
);

const blockingMessage = computed(() => {
  if (isPollingMode.value) {
    return "Polling 模式下覆盖测试不会自动阻断，请按操作手册手动验证并记录结果。";
  }
  switch (statusValue.value) {
    case "green":
      return "覆盖测试通过，可继续配置或启用渠道。";
    case "yellow":
      return "覆盖测试需要关注，请重新运行测试确认行为。";
    case "red":
      return "覆盖测试未通过，禁止启用渠道，请修复问题后重试。";
    default:
      return "尚未运行覆盖测试，请先运行测试以解锁渠道配置。";
  }
});
</script>

<style scoped>
.coverage-gate {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  background: var(--color-bg-subtle);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.coverage-gate__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.coverage-gate__status {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}

.coverage-gate__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #94a3b8;
}

.coverage-gate__dot.is-green {
  background: #12b76a;
}

.coverage-gate__dot.is-yellow {
  background: #f79009;
}

.coverage-gate__dot.is-red {
  background: #f04438;
}

.coverage-gate__timestamp {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.coverage-gate__mode {
  margin: 0;
  font-size: var(--font-size-xs);
  color: #f79009;
}

.coverage-gate__hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.coverage-gate__scenarios {
  margin: 0;
  padding-left: 1rem;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.coverage-gate__error {
  margin: 0;
  color: #f04438;
  font-size: var(--font-size-xs);
}
</style>
