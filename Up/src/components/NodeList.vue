<template>
  <aside class="node-list">
    <header class="node-list__header">
      <h3>节点列表</h3>
      <button type="button" class="node-list__refresh" @click="$emit('refresh')">
        刷新
      </button>
    </header>
    <ul>
      <li
        v-for="node in nodes"
        :key="node.id"
        :class="['node-list__item', { 'node-list__item--active': node.id === selectedNodeId }]"
      >
        <button type="button" class="node-list__content" @click="select(node.id)">
          <div class="node-list__title">{{ node.name || '(未命名节点)' }}</div>
          <div class="node-list__meta">
            <span>{{ formatDate(node.updatedAt || node.createdAt) }}</span>
            <span>{{ node.allowLLM ? 'LLM 可用' : 'LLM 禁止' }}</span>
          </div>
        </button>
        <button
          type="button"
          class="node-list__delete"
          @click.stop="requestDelete(node)"
          aria-label="删除节点"
        >
          删除
        </button>
      </li>
      <li v-if="!nodes.length" class="node-list__empty">暂无节点数据</li>
    </ul>
  </aside>
</template>

<script setup>
import { computed } from "vue";

import { usePipelineDraftStore } from "../stores/pipelineDraft";

const emit = defineEmits(["refresh", "delete"]);

const store = usePipelineDraftStore();

const nodes = computed(() => store.nodes);
const selectedNodeId = computed(() => store.selectedNodeId);

const select = (id) => {
  store.setSelectedNode(id);
};

const requestDelete = (node) => {
  if (!node?.id) return;
  emit("delete", node);
};

const formatDate = (value) => {
  if (!value) return "--";
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value;
  }
};
</script>

<style scoped>
.node-list {
  width: 320px;
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-panel);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
  overflow-y: auto;
}

.node-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.node-list__header h3 {
  margin: 0;
  font-size: var(--font-size-md);
}

.node-list__refresh {
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
  border-radius: var(--radius-xs);
  padding: 4px 8px;
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.node-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.node-list__item {
  display: flex;
  align-items: stretch;
  gap: var(--space-1);
}

.node-list__content {
  flex: 1;
  text-align: left;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  background: transparent;
}

.node-list__content:hover {
  background: var(--color-bg-muted);
}

.node-list__item--active .node-list__content {
  border-color: var(--color-accent-primary);
  background: rgba(255, 69, 0, 0.12);
}

.node-list__title {
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.node-list__meta {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.node-list__delete {
  align-self: center;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
  border-radius: var(--radius-xs);
  padding: 4px 6px;
  font-size: var(--font-size-xs);
  cursor: pointer;
  color: var(--color-text-secondary);
}

.node-list__delete:hover {
  background: rgba(255, 69, 0, 0.12);
  color: var(--color-accent-primary);
}

.node-list__empty {
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
</style>
