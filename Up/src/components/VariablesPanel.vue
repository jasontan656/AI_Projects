<template>
  <section class="variables-panel">
    <header class="variables-panel__header">
      <div>
        <h2>变量面板</h2>
        <p>浏览 Redis / 运行时变量，支持搜索与复制。</p>
      </div>
      <el-input
        v-model="query"
        placeholder="搜索变量名称或值"
        clearable
        class="variables-panel__search"
      >
        <template #prefix>
          <span class="variables-panel__icon">🔍</span>
        </template>
      </el-input>
    </header>

    <el-scrollbar class="variables-panel__list">
      <div
        v-for="variable in filteredVariables"
        :key="variable.key"
        class="variables-panel__item"
      >
        <div class="variables-panel__meta">
          <span class="variables-panel__key">{{ variable.key }}</span>
          <el-button size="small" text type="primary" @click="copy(variable.value)">
            复制
          </el-button>
        </div>
        <pre class="variables-panel__value">{{ variable.value }}</pre>
      </div>

      <el-empty
        v-if="!filteredVariables.length"
        description="暂无匹配变量，等待后端接入或调整筛选条件。"
      />
    </el-scrollbar>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { useStorage } from "@vueuse/core";

const DEFAULT_VARIABLES = [
  { key: "session.userId", value: "ops_admin_001" },
  { key: "session.locale", value: "zh-CN" },
  { key: "context.customer.tier", value: "gold" },
  { key: "context.ticket.id", value: "TCK-2025-1105" },
];

const persisted = useStorage("up.variables.preview", DEFAULT_VARIABLES);
const query = ref("");

const filteredVariables = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  if (!keyword) {
    return persisted.value;
  }
  return (persisted.value || []).filter((item) => {
    const key = item.key?.toLowerCase() || "";
    const value = String(item.value ?? "").toLowerCase();
    return key.includes(keyword) || value.includes(keyword);
  });
});

const copy = async (value) => {
  try {
    await navigator.clipboard.writeText(String(value ?? ""));
    ElMessage.success("已复制到剪贴板");
  } catch (error) {
    ElMessage.error("复制失败，请手动选择文本");
    console.warn("Copy failed", error);
  }
};
</script>

<style scoped>
.variables-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel);
  min-height: 420px;
}

.variables-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.variables-panel__header h2 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.variables-panel__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.variables-panel__search {
  max-width: 320px;
}

.variables-panel__icon {
  display: inline-flex;
  align-items: center;
}

.variables-panel__list {
  flex: 1;
  background: var(--color-bg-muted);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-subtle);
  padding: var(--space-3);
}

.variables-panel__item {
  background: #fff;
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  margin-bottom: var(--space-2);
  box-shadow: var(--shadow-panel);
}

.variables-panel__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.variables-panel__key {
  font-weight: 600;
  font-size: var(--font-size-sm);
}

.variables-panel__value {
  margin: var(--space-1) 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}
</style>
