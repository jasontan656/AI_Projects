<template>
  <aside class="prompt-list">
    <header class="prompt-list__header">
      <h3>提示词列表</h3>
      <button type="button" class="prompt-list__refresh" @click="$emit('refresh')">
        刷新
      </button>
    </header>
    <ul>
      <li
        v-for="prompt in prompts"
        :key="prompt.id"
        :class="['prompt-list__item', { 'prompt-list__item--active': prompt.id === selectedPromptId }]"
      >
        <button type="button" class="prompt-list__content" @click="select(prompt.id)">
          <div class="prompt-list__title">{{ prompt.name || '(未命名提示词)' }}</div>
          <div class="prompt-list__meta">{{ formatDate(prompt.updatedAt || prompt.createdAt) }}</div>
        </button>
        <button
          type="button"
          class="prompt-list__delete"
          @click.stop="requestDelete(prompt)"
          aria-label="删除提示词"
        >
          删除
        </button>
      </li>
      <li v-if="!prompts.length" class="prompt-list__empty">暂无提示词数据</li>
    </ul>
  </aside>
</template>

<script setup>
import { computed } from "vue";

import { usePromptDraftStore } from "../stores/promptDraft";

const emit = defineEmits(["refresh", "delete"]);

const store = usePromptDraftStore();

const prompts = computed(() => store.prompts);
const selectedPromptId = computed(() => store.selectedPromptId);

const select = (id) => {
  store.setSelectedPrompt(id);
};

const requestDelete = (prompt) => {
  if (!prompt?.id) return;
  emit("delete", prompt);
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
.prompt-list {
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

.prompt-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.prompt-list__header h3 {
  margin: 0;
  font-size: var(--font-size-md);
}

.prompt-list__refresh {
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
  border-radius: var(--radius-xs);
  padding: 4px 8px;
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.prompt-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.prompt-list__item {
  display: flex;
  align-items: stretch;
  gap: var(--space-1);
}

.prompt-list__content {
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

.prompt-list__content:hover {
  background: var(--color-bg-muted);
}

.prompt-list__item--active .prompt-list__content {
  border-color: var(--color-accent-primary);
  background: rgba(255, 69, 0, 0.12);
}

.prompt-list__title {
  font-size: var(--font-size-sm);
  font-weight: 600;
}

.prompt-list__meta {
  display: flex;
  justify-content: flex-start;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.prompt-list__delete {
  align-self: center;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
  border-radius: var(--radius-xs);
  padding: 4px 6px;
  font-size: var(--font-size-xs);
  cursor: pointer;
  color: var(--color-text-secondary);
}

.prompt-list__delete:hover {
  background: rgba(255, 69, 0, 0.12);
  color: var(--color-accent-primary);
}

.prompt-list__empty {
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
</style>
