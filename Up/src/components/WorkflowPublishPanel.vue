<template>
  <section class="workflow-publish">
    <header class="workflow-publish__header">
      <div>
        <h3>发布与历史版本</h3>
        <p>确认当前配置后发布，或从历史版本回滚。</p>
      </div>
      <div class="workflow-publish__actions">
        <el-button
          type="primary"
          :loading="publishing"
          :disabled="disabled"
          @click="handlePublish"
        >
          发布
        </el-button>
      </div>
    </header>

    <section class="workflow-publish__summary">
      <p>当前状态：<strong>{{ workflow.status === "published" ? "已发布" : "草稿" }}</strong></p>
      <p>版本：v{{ workflow.version ?? 0 }}</p>
      <p>上次更新：{{ formatDate(workflow.updatedAt || workflow.createdAt) }}</p>
    </section>

    <section class="workflow-publish__history">
      <header>
        <h4>历史记录</h4>
        <el-button link size="small" :loading="refreshing" @click="$emit('refresh')">
          刷新
        </el-button>
      </header>
      <el-empty v-if="!history.length" description="暂无发布记录" />
      <ul v-else class="workflow-publish__history-list">
        <li v-for="item in history" :key="item.version" class="workflow-publish__history-item">
          <div>
            <strong>v{{ item.version }}</strong> · {{ item.operator || "未知" }}
            <p class="workflow-publish__history-meta">
              {{ formatDate(item.timestamp) }} · {{ item.notes || "未填写备注" }}
            </p>
          </div>
          <el-button
            size="small"
            text
            :loading="rollingBack && targetVersion === item.version"
            @click="handleRollback(item.version)"
          >
            回滚
          </el-button>
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
  workflow: {
    type: Object,
    default: () => ({}),
  },
  history: {
    type: Array,
    default: () => [],
  },
  publishing: {
    type: Boolean,
    default: false,
  },
  rollingBack: {
    type: Boolean,
    default: false,
  },
  refreshing: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["publish", "rollback", "refresh"]);

const targetVersion = ref(null);

const handlePublish = () => {
  emit("publish");
};

const handleRollback = (version) => {
  targetVersion.value = version;
  emit("rollback", version);
};

const formatDate = (value) => {
  if (!value) return "--";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};
</script>

<style scoped>
.workflow-publish {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  height: 100%;
}

.workflow-publish__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: flex-start;
}

.workflow-publish__header h3 {
  margin: 0;
}

.workflow-publish__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.workflow-publish__actions {
  display: flex;
  gap: var(--space-2);
}

.workflow-publish__summary {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.workflow-publish__history header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.workflow-publish__history-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 320px;
  overflow-y: auto;
}

.workflow-publish__history-item {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
}

.workflow-publish__history-meta {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}
</style>
