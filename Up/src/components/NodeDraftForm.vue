<template>
  <section class="node-draft">
    <header class="node-draft__header">
      <h2>{{ isEditing ? "编辑节点" : "新增节点" }}</h2>
      <p>填写节点元数据与脚本动作，保存后用于驱动后端契约实现。</p>
    </header>

    <form class="node-draft__form" @submit.prevent="handleSubmit">
      <label class="node-draft__label" for="node-name">节点名称</label>
      <input
        id="node-name"
        ref="nameField"
        v-model="form.name"
        class="node-draft__input"
        type="text"
        placeholder="请输入节点名称"
        autofocus
      />
      <p v-if="errors.name" class="node-draft__error">{{ errors.name }}</p>

      <label class="node-draft__toggle">
        <input v-model="form.allowLLM" type="checkbox" />
        <span>允许访问大模型</span>
      </label>

      <section class="node-draft__actions">
        <div class="node-draft__actions-header">
          <span class="node-draft__label">节点动作</span>
          <p class="node-draft__hint">
            通过预定义动作拼接节点执行脚本。当允许访问大模型时，可引用提示词模板。
          </p>
        </div>
        <NodeActionList
          v-model="form.actions"
          :allow-llm="form.allowLLM"
          :prompt-templates="promptTemplates"
          @open-settings="handleOpenActionSettings"
        />
        <p
          v-if="!form.allowLLM && hasPromptActions(form.actions)"
          class="node-draft__warning"
        >
          当前节点未允许访问大模型，请先移除提示词动作或重新启用大模型。
        </p>
        <p v-if="errors.actions" class="node-draft__error">{{ errors.actions }}</p>
      </section>

      <footer class="node-draft__footer">
        <button type="button" class="node-draft__ghost" @click="handleReset" :disabled="isSaving">
          重置
        </button>
        <button type="submit" class="node-draft__submit" :disabled="isSaving">
          {{ isSaving ? "保存中…" : isEditing ? "更新节点" : "保存节点" }}
        </button>
      </footer>
    </form>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessageBox } from "element-plus";

import NodeActionList from "./NodeActionList.vue";
import { usePipelineDraftStore } from "../stores/pipelineDraft";
import { usePromptDraftStore } from "../stores/promptDraft";
import {
  createPipelineNode,
  listPipelineNodes,
  updatePipelineNode,
} from "../services/pipelineService";
import { listPromptDrafts } from "../services/promptService";
import { ACTION_TYPES, cloneActions, hasPromptActions } from "../utils/nodeActions";

const pipelineStore = usePipelineDraftStore();
const promptStore = usePromptDraftStore();

const form = reactive({
  name: "",
  allowLLM: true,
  actions: [],
});

const isSaving = ref(false);
const errors = reactive({ name: "", actions: "" });
const nameField = ref(null);

const selectedNode = computed(() => pipelineStore.selectedNode);
const isEditing = computed(() => Boolean(selectedNode.value));

const formatTimestamp = (value) => {
  if (!value) return "未知时间";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
};

const promptTemplates = computed(() =>
  (promptStore.prompts || []).map((template) => ({
    id: template.id,
    name: template.name || "(未命名提示词)",
    updatedLabel: formatTimestamp(template.updatedAt || template.createdAt),
    markdown: template.markdown || "",
  }))
);

const describeActionType = (type) => {
  switch (type) {
    case ACTION_TYPES.PROMPT_APPEND:
      return "提示词拼接";
    case ACTION_TYPES.TOOL_INVOKE:
      return "工具调用";
    case ACTION_TYPES.EMIT_OUTPUT:
      return "输出结果";
    default:
      return type || "自定义动作";
  }
};

const escapeHtml = (text = "") =>
  String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

const handleOpenActionSettings = (action) => {
  if (!action) return;
  const summary = `
    <p><strong>类型：</strong>${describeActionType(action.type)}</p>
    <p><strong>顺序：</strong>${(action.order ?? 0) + 1}</p>
    <p><strong>配置：</strong></p>
    <pre>${escapeHtml(JSON.stringify(action.config ?? {}, null, 2))}</pre>
  `;
  ElMessageBox.alert(summary, "动作设置", {
    confirmButtonText: "知道了",
    dangerouslyUseHTMLString: true,
  }).catch(() => {});
};

const focusName = () => {
  nameField.value?.focus();
};

const populateForm = (node) => {
  if (!node) {
    form.name = "";
    form.allowLLM = true;
    form.actions = [];
    errors.name = "";
    errors.actions = "";
    return;
  }
  form.name = node.name || "";
  form.allowLLM = Boolean(node.allowLLM);
  form.actions = cloneActions(node.actions || []);
  errors.name = "";
  errors.actions = "";
};

const fetchNodes = async () => {
  try {
    const response = await listPipelineNodes({ pageSize: 50 });
    const items = Array.isArray(response?.items)
      ? response.items
      : Array.isArray(response)
      ? response
      : [];
    pipelineStore.replaceNodes(items);
  } catch (error) {
    console.warn("加载节点列表失败", error);
  }
};

const ensurePromptTemplates = async () => {
  if (promptStore.prompts.length) return;
  try {
    const response = await listPromptDrafts({ pageSize: 100 });
    const items = Array.isArray(response?.items)
      ? response.items
      : Array.isArray(response)
      ? response
      : [];
    promptStore.replacePrompts(items);
  } catch (error) {
    console.warn("加载提示词模板失败", error);
  }
};

const handleReset = () => {
  populateForm(selectedNode.value || null);
  focusName();
};

const newEntry = () => {
  pipelineStore.resetSelection();
  populateForm(null);
  focusName();
};

const handleSubmit = async () => {
  errors.name = "";
  errors.actions = "";

  if (!form.name.trim()) {
    errors.name = "节点名称不能为空";
    return;
  }

  if (!form.allowLLM && hasPromptActions(form.actions)) {
    errors.actions = "禁用大模型时不能包含提示词动作";
    return;
  }

  try {
    isSaving.value = true;
    const payload = {
      name: form.name,
      allowLLM: form.allowLLM,
      actions: cloneActions(form.actions),
      pipelineId: selectedNode.value?.pipelineId,
      status: selectedNode.value?.status,
      strategy: selectedNode.value?.strategy,
    };

    if (selectedNode.value) {
      await updatePipelineNode(selectedNode.value.id, payload);
    } else {
      await createPipelineNode(payload);
      pipelineStore.resetSelection();
      populateForm(null);
    }

    await fetchNodes();
    populateForm(selectedNode.value || null);
    if (!selectedNode.value) {
      focusName();
    }
  } catch (error) {
    errors.name = error.message || "保存失败";
  } finally {
    isSaving.value = false;
  }
};

watch(
  () => form.name,
  () => {
    if (errors.name) {
      errors.name = "";
    }
  }
);

watch(
  () => form.actions,
  () => {
    if (errors.actions) {
      errors.actions = "";
    }
  },
  { deep: true }
);

watch(
  selectedNode,
  (node) => {
    populateForm(node || null);
  },
  { immediate: true }
);

watch(
  () => form.allowLLM,
  (value) => {
    if (value && errors.actions) {
      errors.actions = "";
    }
    const synced = cloneActions(form.actions).map((action, index) => ({
      ...action,
      order: index,
      disabled:
        action.type === ACTION_TYPES.PROMPT_APPEND ? !value : action.disabled ?? false,
    }));
    form.actions = synced;
  }
);

onMounted(async () => {
  await Promise.all([fetchNodes(), ensurePromptTemplates()]);
  focusName();
});

defineExpose({ refresh: fetchNodes, newEntry });
</script>

<style scoped>
.node-draft {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
  max-width: 960px;
}

.node-draft__header h2 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.node-draft__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.node-draft__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-panel);
}

.node-draft__label {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.node-draft__input {
  width: 100%;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  padding: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: #fff;
}

.node-draft__toggle {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.node-draft__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.node-draft__actions-header {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.node-draft__hint {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.node-draft__warning {
  margin: 0;
  font-size: var(--font-size-xs);
  color: #e03131;
}

.node-draft__footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-1);
}

.node-draft__submit,
.node-draft__ghost {
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.node-draft__ghost {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-subtle);
}

.node-draft__submit {
  background: var(--color-accent-primary);
  color: #fff;
}

.node-draft__submit:disabled,
.node-draft__ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.node-draft__error {
  color: #e03131;
  font-size: var(--font-size-xs);
  margin: 0;
}
</style>
