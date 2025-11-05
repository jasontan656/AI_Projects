<template>
  <section class="node-action-list">
    <div class="node-action-list__toolbar">
      <button
        type="button"
        class="node-action-list__add"
        :disabled="!allowLlm"
        @click="addPromptAction"
        @mousedown.stop
      >
        添加提示词动作
      </button>
      <button type="button" class="node-action-list__add" disabled>
        添加工具动作（即将上线）
      </button>
    </div>

    <p v-if="!sortedActions.length" class="node-action-list__empty">
      尚未添加任何动作。
    </p>

    <ul v-else class="node-action-list__items">
      <li
        v-for="(action, index) in sortedActions"
        :key="action.id"
        class="node-action-card"
        :class="{
          'node-action-card--prompt': action.type === ACTION_TYPES.PROMPT_APPEND,
          'node-action-card--llm-disabled':
            action.type === ACTION_TYPES.PROMPT_APPEND && !allowLlm,
        }"
        @contextmenu.prevent="openContextMenu($event, action)"
      >
        <header class="node-action-card__header">
          <span class="node-action-card__title">
            动作 {{ index + 1 }} · {{ actionLabel(action) }}
          </span>
          <div class="node-action-card__controls">
            <button
              type="button"
              class="node-action-card__control"
              :disabled="index === 0"
              @click="moveAction(action.id, -1)"
            >
              上移
            </button>
            <button
              type="button"
              class="node-action-card__control"
              :disabled="index === sortedActions.length - 1"
              @click="moveAction(action.id, 1)"
            >
              下移
            </button>
            <button
              type="button"
              class="node-action-card__control node-action-card__control--danger"
              @click="removeAction(action.id)"
            >
              删除
            </button>
          </div>
        </header>

        <div v-if="action.type === ACTION_TYPES.PROMPT_APPEND" class="node-action-card__body">
          <label class="node-action-card__label" for="template-select">
            选择提示词模板
          </label>
          <select
            id="template-select"
            class="node-action-card__select"
            :disabled="!allowLlm"
            :value="action.config?.templateId ?? ''"
            @change="updatePromptTemplate(action.id, $event.target.value)"
          >
            <option value="">请选择模板</option>
            <option
              v-for="template in promptTemplates"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }}（更新于 {{ template.updatedLabel }}）
            </option>
          </select>

          <p v-if="templateDisplay(action)" class="node-action-card__meta">
            {{ templateDisplay(action) }}
          </p>

          <div class="node-action-card__preview">
            <p class="node-action-card__label">模板内容预览</p>
            <div
              v-if="templateBody(action)"
              class="node-action-card__preview-body"
              v-html="templateBody(action)"
            ></div>
            <p v-else class="node-action-card__meta">尚未选择模板，无法显示内容。</p>
          </div>

          <p
            v-if="!allowLlm"
            class="node-action-card__warning"
          >
            当前节点未允许访问大模型，请移除此动作或重新启用大模型。
          </p>
        </div>

        <div v-else class="node-action-card__body">
          <p class="node-action-card__meta">
            该动作类型尚未实现配置界面。
          </p>
        </div>
      </li>
    </ul>

    <teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="node-action-context"
        :style="{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }"
      >
        <button type="button" class="node-action-context__item" @click="handleContextSelect('settings')">
          查看设置
        </button>
        <button type="button" class="node-action-context__item" @click="handleContextSelect('remove')">
          删除动作
        </button>
        <button type="button" class="node-action-context__item" @click="handleContextSelect('duplicate')">
          复制动作
        </button>
      </div>
    </teleport>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive } from "vue";
import { v4 as uuid } from "uuid";

import {
  ACTION_TYPES,
  cloneActions,
  createPromptAppendAction,
} from "../utils/nodeActions";

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  allowLlm: {
    type: Boolean,
    default: true,
  },
  promptTemplates: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["update:modelValue", "open-settings"]);

const promptMap = computed(() => {
  const map = new Map();
  props.promptTemplates.forEach((template) => {
    map.set(template.id, template);
  });
  return map;
});

const sortedActions = computed(() =>
  cloneActions(props.modelValue).sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
);

const commit = (actions) => {
  const normalized = actions.map((action, index) => ({
    ...action,
    order: index,
    disabled:
      action.type === ACTION_TYPES.PROMPT_APPEND ? !props.allowLlm : action.disabled ?? false,
  }));
  emit("update:modelValue", normalized);
};

const addPromptAction = () => {
  if (!props.allowLlm) return;
  const actions = cloneActions(props.modelValue);
  const order = actions.length;
  actions.push(createPromptAppendAction({ order }));
  commit(actions);
};

const removeAction = (id) => {
  const actions = cloneActions(props.modelValue).filter((action) => action.id !== id);
  commit(actions);
};

const moveAction = (id, direction) => {
  const actions = cloneActions(props.modelValue);
  const index = actions.findIndex((action) => action.id === id);
  if (index === -1) return;
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= actions.length) return;
  const [moved] = actions.splice(index, 1);
  actions.splice(targetIndex, 0, moved);
  commit(actions);
};

const updatePromptTemplate = (id, templateId) => {
  const actions = cloneActions(props.modelValue);
  const index = actions.findIndex((action) => action.id === id);
  if (index === -1) return;
  actions[index] = {
    ...actions[index],
    config: {
      ...(actions[index].config || {}),
      templateId: templateId || null,
    },
  };
  commit(actions);
};

const actionLabel = (action) => {
  switch (action.type) {
    case ACTION_TYPES.PROMPT_APPEND:
      return "提示词拼接";
    case ACTION_TYPES.TOOL_INVOKE:
      return "工具调用";
    case ACTION_TYPES.EMIT_OUTPUT:
      return "输出结果";
    default:
      return action.type || "自定义动作";
  }
};

const templateDisplay = (action) => {
  if (action.type !== ACTION_TYPES.PROMPT_APPEND) return "";
  const templateId = action.config?.templateId;
  if (!templateId) return "";
  const template = promptMap.value.get(templateId);
  if (!template) return `模板 ${templateId}`;
  return `已选模板：${template.name}`;
};

const normalizeMarkdown = (markdown = "") =>
  markdown
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br />");

const templateBody = (action) => {
  if (action.type !== ACTION_TYPES.PROMPT_APPEND) return "";
  const templateId = action.config?.templateId;
  if (!templateId) {
    const legacy = action.config?.legacyText;
    return legacy ? normalizeMarkdown(legacy) : "";
  }
  const template = promptMap.value.get(templateId);
  if (!template) return "";
  return normalizeMarkdown(template.markdown || "");
};

const duplicateAction = (id) => {
  const actions = cloneActions(props.modelValue);
  const index = actions.findIndex((action) => action.id === id);
  if (index === -1) return;
  const source = actions[index];
  const copy = {
    ...source,
    id: uuid(),
    order: actions.length,
    config: { ...(source.config || {}) },
  };
  actions.splice(index + 1, 0, copy);
  commit(actions);
};

const contextMenu = reactive({
  visible: false,
  x: 0,
  y: 0,
  actionId: null,
});

const closeContextMenu = () => {
  contextMenu.visible = false;
  contextMenu.actionId = null;
};

const openContextMenu = (event, action) => {
  event.stopPropagation();
  contextMenu.visible = true;
  contextMenu.x = event.clientX;
  contextMenu.y = event.clientY;
  contextMenu.actionId = action?.id ?? null;
};

const handleContextSelect = (command) => {
  if (!contextMenu.actionId) {
    closeContextMenu();
    return;
  }
  const action = sortedActions.value.find((item) => item.id === contextMenu.actionId);
  if (command === "settings" && action) {
    emit("open-settings", { ...action, config: { ...(action.config || {}) } });
  } else if (command === "remove") {
    removeAction(contextMenu.actionId);
  } else if (command === "duplicate") {
    duplicateAction(contextMenu.actionId);
  }
  closeContextMenu();
};

const handlePointerDown = () => {
  if (contextMenu.visible) {
    closeContextMenu();
  }
};

const handleKeydown = (event) => {
  if (event.key === "Escape" && contextMenu.visible) {
    closeContextMenu();
  }
};

onMounted(() => {
  window.addEventListener("pointerdown", handlePointerDown);
  window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  window.removeEventListener("pointerdown", handlePointerDown);
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.node-action-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.node-action-list__toolbar {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.node-action-list__add {
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
  border-radius: var(--radius-xs);
  padding: var(--space-1) var(--space-2);
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.node-action-list__add:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.node-action-list__empty {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.node-action-list__items {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.node-action-card {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  background: var(--color-bg-panel);
  box-shadow: var(--shadow-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.node-action-card--llm-disabled {
  border-color: rgba(255, 69, 0, 0.35);
}

.node-action-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2);
}

.node-action-card__title {
  font-weight: 600;
  font-size: var(--font-size-sm);
}

.node-action-card__controls {
  display: flex;
  gap: var(--space-1);
}

.node-action-card__control {
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-muted);
  border-radius: var(--radius-xs);
  padding: var(--space-1) var(--space-2);
  font-size: var(--font-size-xs);
  cursor: pointer;
}

.node-action-card__control:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.node-action-card__control--danger {
  border-color: rgba(224, 49, 49, 0.25);
  color: #e03131;
}

.node-action-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.node-action-card__label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
}

.node-action-card__select {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-xs);
  padding: var(--space-1) var(--space-2);
  font-size: var(--font-size-sm);
}

.node-action-card__meta {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.node-action-card__preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  background: var(--color-bg-muted);
  border-radius: var(--radius-xs);
  border: 1px solid var(--color-border-subtle);
  padding: var(--space-2);
}

.node-action-card__preview-body {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  line-height: var(--line-height-base);
  word-break: break-word;
  white-space: normal;
}

.node-action-card__warning {
  margin: 0;
  font-size: var(--font-size-xs);
  color: #e03131;
}

.node-action-context {
  position: fixed;
  z-index: 2000;
  min-width: 160px;
  background: #fff;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-panel);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.node-action-context__item {
  padding: 10px 14px;
  background: transparent;
  border: none;
  text-align: left;
  font-size: var(--font-size-sm);
  cursor: pointer;
}

.node-action-context__item:hover {
  background: var(--color-bg-muted);
}
</style>
