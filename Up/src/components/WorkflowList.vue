<template>
  <aside class="workflow-list">
    <header class="workflow-list__header">
      <div>
        <h3>Workflow</h3>
        <p class="workflow-list__meta">同步 Rise 编排记录</p>
      </div>
      <div class="workflow-list__actions">
        <el-button size="small" text :loading="loading" @click="$emit('refresh')">
          刷新
        </el-button>
        <el-button size="small" type="primary" @click="$emit('create')">
          新建
        </el-button>
      </div>
    </header>

    <el-input
      v-model="keyword"
      class="workflow-list__search"
      placeholder="搜索 Workflow"
      size="small"
      clearable
      @input="handleSearchInput"
    />

    <ul class="workflow-list__items">
      <li
        v-for="workflow in filtered"
        :key="workflow.id"
        :class="['workflow-list__item', { 'workflow-list__item--active': workflow.id === selectedId }]"
      >
        <button type="button" class="workflow-list__content" @click="$emit('select', workflow.id)">
          <div class="workflow-list__title-row">
            <span class="workflow-list__title">{{ workflow.name || "(未命名 Workflow)" }}</span>
            <span :class="['workflow-list__badge', `is-${workflow.status || 'draft'}`]">
              {{ workflow.status === "published" ? "已发布" : "草稿" }}
            </span>
          </div>
          <p class="workflow-list__info">版本 v{{ workflow.version ?? 0 }}</p>
          <p class="workflow-list__info">
            {{ workflow.updatedBy || workflow.createdBy || "未知" }} ·
            {{ formatDate(workflow.updatedAt || workflow.createdAt) }}
          </p>
        </button>
        <el-popconfirm
          placement="left"
          width="220"
          :title="`确认删除 Workflow「${workflow.name || workflow.id}」？`"
          confirm-button-text="确认删除"
          cancel-button-text="取消"
          :disabled="workflow.status === 'published'"
          @confirm="handleRemove(workflow)"
        >
          <template #reference>
            <el-button
              class="workflow-list__delete"
              link
              type="danger"
              :disabled="workflow.status === 'published'"
            >
              删除
            </el-button>
          </template>
        </el-popconfirm>
      </li>
      <li v-if="!filtered.length" class="workflow-list__empty">
        无 Workflow，请点击右上角“新建”。
      </li>
    </ul>
  </aside>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  workflows: {
    type: Array,
    default: () => [],
  },
  selectedId: {
    type: [String, Number, null],
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["select", "create", "remove", "search", "refresh"]);

const keyword = ref("");

const handleRemove = (workflow) => {
  emit("remove", workflow);
};

const filtered = computed(() => {
  if (!keyword.value) {
    return props.workflows;
  }
  const text = keyword.value.toLowerCase();
  return props.workflows.filter((item) =>
    (item.name || "").toLowerCase().includes(text)
  );
});

const handleSearchInput = () => {
  emit("search", keyword.value.trim());
};

const formatDate = (value) => {
  if (!value) return "--";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

watch(
  () => props.workflows,
  () => {
    if (!props.workflows.length) {
      keyword.value = "";
    }
  }
);
</script>

<style scoped>
.workflow-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-panel);
  box-shadow: var(--shadow-panel);
  height: 100%;
  min-width: 0;
}

.workflow-list__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: flex-start;
}

.workflow-list__header h3 {
  margin: 0;
  font-size: var(--font-size-md);
}

.workflow-list__meta {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.workflow-list__actions {
  display: flex;
  gap: var(--space-1);
}

.workflow-list__search {
  width: 100%;
}

.workflow-list__items {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  overflow-y: auto;
}

.workflow-list__item {
  display: flex;
  gap: var(--space-1);
  align-items: stretch;
}

.workflow-list__item--active .workflow-list__content {
  border-color: var(--color-accent-primary);
  background: rgba(255, 69, 0, 0.08);
}

.workflow-list__content {
  flex: 1;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-subtle);
  padding: var(--space-2);
  background: transparent;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  transition: border-color 0.2s ease, background 0.2s ease;
}

.workflow-list__title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
}

.workflow-list__title {
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.workflow-list__badge {
  font-size: var(--font-size-2xs);
  border-radius: var(--radius-pill);
  padding: 0 var(--space-2);
  line-height: 18px;
}

.workflow-list__badge.is-published {
  background: rgba(0, 163, 64, 0.16);
  color: #00753a;
}

.workflow-list__badge.is-draft {
  background: rgba(255, 178, 43, 0.2);
  color: #a45c00;
}

.workflow-list__info {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.workflow-list__delete {
  align-self: center;
  font-size: var(--font-size-xs);
}

.workflow-list__empty {
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  padding: var(--space-2);
  border: 1px dashed var(--color-border-subtle);
  border-radius: var(--radius-sm);
}
</style>
