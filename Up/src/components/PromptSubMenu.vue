<template>
  <el-card class="prompt-submenu" shadow="never">
    <header class="prompt-submenu__header">
      <h3>提示词操作</h3>
      <p>请选择要执行的提示词工作流阶段。</p>
    </header>
    <div class="prompt-submenu__grid" role="list">
      <article
        v-for="action in normalizedActions"
        :key="action.id"
        class="prompt-submenu__item"
        role="listitem"
        :aria-disabled="action.disabled"
      >
        <div class="prompt-submenu__body">
          <div v-if="action.icon" class="prompt-submenu__icon" aria-hidden="true">
            <component :is="action.icon" />
          </div>
          <div class="prompt-submenu__text">
            <h4>{{ action.label }}</h4>
            <p class="prompt-submenu__description">{{ action.description }}</p>
            <p
              v-if="action.disabled && action.reason"
              :id="`prompt-submenu-hint-${action.id}`"
              class="prompt-submenu__hint"
            >
              {{ action.reason }}
            </p>
          </div>
        </div>
        <el-button
          class="prompt-submenu__trigger"
          :type="action.ctaType"
          :text="action.textButton"
          :disabled="action.disabled"
          :aria-label="action.label"
          :aria-describedby="
            action.disabled && action.reason ? `prompt-submenu-hint-${action.id}` : undefined
          "
          @click="emitSelect(action)"
          @keyup.enter="emitSelect(action)"
        >
          {{ action.ctaLabel }}
        </el-button>
      </article>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  actions: {
    type: Array,
    default: () => [
      {
        id: "create",
        label: "新建提示词",
        description: "从空白草稿快速写作 Markdown 模板。",
        stage: "create",
        ctaLabel: "开始创建",
        ctaType: "primary",
      },
      {
        id: "manage",
        label: "管理提示词",
        description: "浏览与维护既有模板，支持编辑/删除。",
        stage: "manage",
        ctaLabel: "进入管理",
      },
    ],
  },
});

const emit = defineEmits(["select"]);

const normalizedActions = computed(() =>
  (props.actions || []).map((action) => {
    const guardResult = typeof action.guard === "function" ? action.guard() : null;
    const guardDisabled =
      typeof guardResult === "boolean"
        ? guardResult
        : guardResult && typeof guardResult === "object"
        ? Boolean(guardResult.disabled)
        : false;
    const disabled = typeof action.disabled === "boolean" ? action.disabled : guardDisabled;
    const reason =
      action.reason ||
      action.disabledReason ||
      (typeof guardResult === "string" ? guardResult : guardResult?.reason) ||
      "";

    const textButton = typeof action.textButton === "boolean" ? action.textButton : false;

    const resolvedType =
      action.ctaType !== undefined
        ? action.ctaType
        : action.stage === "create"
        ? "primary"
        : undefined;

    return {
      ...action,
      disabled,
      reason,
      textButton,
      ctaLabel: action.ctaLabel || (action.stage === "create" ? "开始创建" : "进入"),
      ctaType: resolvedType,
    };
  })
);

const emitSelect = (action) => {
  if (action.disabled) return;
  emit("select", action);
};
</script>

<style scoped>
.prompt-submenu {
  max-width: 760px;
  margin: 0 auto;
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
}

.prompt-submenu__header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.prompt-submenu__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.prompt-submenu__grid {
  display: grid;
  gap: var(--space-3);
}

@media (min-width: 640px) {
  .prompt-submenu__grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }
}

.prompt-submenu__item {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-muted, #f9f9fb);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.prompt-submenu__item[aria-disabled="true"] {
  opacity: 0.6;
}

.prompt-submenu__item:not([aria-disabled="true"]):hover {
  border-color: var(--color-accent-primary);
  box-shadow: var(--shadow-panel);
}

.prompt-submenu__body {
  display: flex;
  gap: var(--space-3);
  align-items: flex-start;
}

.prompt-submenu__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: rgba(255, 69, 0, 0.12);
  color: var(--color-accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.prompt-submenu__icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.prompt-submenu__text h4 {
  margin: 0;
  font-size: var(--font-size-md);
}

.prompt-submenu__description {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.prompt-submenu__hint {
  margin: var(--space-2) 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.prompt-submenu__trigger {
  align-self: flex-start;
}
</style>
