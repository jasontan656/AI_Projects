<template>
  <section class="execution-strategy-form">
    <header class="execution-strategy-form__header">
      <div>
        <h3>执行策略</h3>
        <p>默认重试 2 次，可根据业务复杂度调整超时与重试次数。</p>
      </div>
    </header>
    <div class="execution-strategy-form__grid">
      <el-form-item
        label="重试次数 (0-5)"
        :error="errors.retryLimit"
        data-test="strategy-retry-item"
      >
        <el-input-number
          :model-value="retryLimit"
          :min="0"
          :max="5"
          :disabled="disabled"
          data-test="strategy-retry"
          @change="(value) => updateRetryLimit(value ?? 0)"
        />
      </el-form-item>
      <el-form-item
        label="超时 (ms)"
        :error="errors.timeoutMs"
        data-test="strategy-timeout-item"
      >
        <el-input-number
          :model-value="timeoutMs"
          :min="0"
          :step="1000"
          :precision="0"
          :disabled="disabled"
          data-test="strategy-timeout"
          @change="(value) => updateTimeout(value ?? 0)"
        />
      </el-form-item>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  strategy: {
    type: Object,
    default: () => ({ retryLimit: 2, timeoutMs: 0 }),
  },
  errors: {
    type: Object,
    default: () => ({}),
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:strategy"]);

const retryLimit = computed(() => props.strategy?.retryLimit ?? 0);
const timeoutMs = computed(() => props.strategy?.timeoutMs ?? 0);

const updateRetryLimit = (value) => {
  emit("update:strategy", {
    ...props.strategy,
    retryLimit: Number.isFinite(value) ? Number(value) : 0,
  });
};

const updateTimeout = (value) => {
  emit("update:strategy", {
    ...props.strategy,
    timeoutMs: Number.isFinite(value) ? Number(value) : 0,
  });
};
</script>

<style scoped>
.execution-strategy-form {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.execution-strategy-form__header h3 {
  margin: 0;
  font-size: 1rem;
}

.execution-strategy-form__header p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 0.875rem;
}

.execution-strategy-form__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}
</style>
