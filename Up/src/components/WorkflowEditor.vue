<template>
  <section class="workflow-editor">
    <header class="workflow-editor__header">
      <div>
        <h2>{{ form.id ? "编辑 Workflow" : "新建 Workflow" }}</h2>
        <p>选择节点顺序并绑定提示词，保存草稿以便发布。</p>
      </div>
      <div class="workflow-editor__actions">
        <el-button @click="handleReset" text :disabled="saving || !form.id">
          放弃更改
        </el-button>
        <el-button type="primary" :loading="saving" :disabled="!canSave" @click="handleSave">
          保存草稿
        </el-button>
      </div>
    </header>

    <el-form label-position="top" :disabled="disabled" class="workflow-editor__form">
      <el-form-item label="Workflow 名称" :error="errors.name">
        <el-input v-model="form.name" placeholder="请输入名称" />
      </el-form-item>

      <el-form-item label="描述">
        <el-input
          v-model="form.metadata.description"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="补充用途、注意事项等"
        />
      </el-form-item>

      <el-form-item label="节点执行顺序" :error="errors.nodeSequence">
        <el-select
          v-model="form.nodeSequence"
          multiple
          filterable
          placeholder="按执行顺序选择节点"
          collapse-tags
          @change="syncPromptBindings"
        >
          <el-option
            v-for="node in nodes"
            :key="node.id"
            :label="node.name || '(未命名节点)'"
            :value="node.id"
          />
        </el-select>
        <p class="workflow-editor__hint">
          选择顺序即执行顺序，可多选；如需移除节点，请在右侧删除对应提示词绑定。
        </p>
      </el-form-item>

      <section class="workflow-editor__binding">
        <header>
          <h3>提示词绑定</h3>
          <p>为每个节点指定提示词模板，未绑定将继承节点自带配置。</p>
        </header>
        <div
          v-if="!form.nodeSequence.length"
          class="workflow-editor__binding-empty"
        >
          请选择节点后再配置提示词。
        </div>
        <div v-else class="workflow-editor__binding-grid">
          <div
            v-for="nodeId in form.nodeSequence"
            :key="nodeId"
            class="workflow-editor__binding-row"
          >
            <div class="workflow-editor__binding-label">
              {{ resolveNodeName(nodeId) }}
            </div>
            <el-select
              v-model="nodePromptMap[nodeId]"
              filterable
              clearable
              placeholder="可选提示词"
              @change="updatePromptBindings"
            >
              <el-option
                v-for="prompt in prompts"
                :key="prompt.id"
                :label="prompt.name || '(未命名提示词)'"
                :value="prompt.id"
              />
            </el-select>
            <el-button
              link
              type="info"
              size="small"
              @click="clearPrompt(nodeId)"
            >
              清除
            </el-button>
          </div>
        </div>
      </section>

      <section class="workflow-editor__strategy">
        <header>
          <h3>执行策略</h3>
        </header>
        <div class="workflow-editor__strategy-grid">
          <el-form-item label="重试次数 (0-5)" :error="errors.retryLimit">
            <el-input-number
              v-model="form.strategy.retryLimit"
              :min="0"
              :max="5"
            />
          </el-form-item>
          <el-form-item label="超时 (ms)" :error="errors.timeoutMs">
            <el-input-number
              v-model="form.strategy.timeoutMs"
              :min="0"
              :step="1000"
              :precision="0"
            />
          </el-form-item>
        </div>
      </section>
    </el-form>
  </section>
</template>

<script setup>
import { computed, reactive, watch, toRaw } from "vue";
import { ElMessage } from "element-plus";

const props = defineProps({
  workflow: {
    type: Object,
    default: () => ({}),
  },
  nodes: {
    type: Array,
    default: () => [],
  },
  prompts: {
    type: Array,
    default: () => [],
  },
  saving: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["save", "dirty-change"]);

const form = reactive({
  id: null,
  name: "",
  status: "draft",
  nodeSequence: [],
  promptBindings: [],
  strategy: { retryLimit: 0, timeoutMs: 0 },
  metadata: { description: "", tags: [] },
});

const baseline = reactive({
  id: null,
  name: "",
  status: "draft",
  nodeSequence: [],
  promptBindings: [],
  strategy: { retryLimit: 0, timeoutMs: 0 },
  metadata: { description: "", tags: [] },
});

const nodePromptMap = reactive({});
const errors = reactive({
  name: "",
  nodeSequence: "",
  retryLimit: "",
  timeoutMs: "",
});

const copyIntoForm = (source = {}) => {
  form.id = source.id || null;
  form.name = source.name || "";
  form.status = source.status || "draft";
  form.nodeSequence = Array.isArray(source.nodeSequence)
    ? [...source.nodeSequence]
    : [];
  form.promptBindings = Array.isArray(source.promptBindings)
    ? source.promptBindings.map((item) => ({ ...item }))
    : [];
  form.strategy = {
    retryLimit: source.strategy?.retryLimit ?? 0,
    timeoutMs: source.strategy?.timeoutMs ?? 0,
  };
  form.metadata = {
    description: source.metadata?.description || "",
    tags: Array.isArray(source.metadata?.tags) ? [...source.metadata.tags] : [],
  };
  resetNodePromptMap();
};

const resetBaseline = () => {
  baseline.id = form.id;
  baseline.name = form.name;
  baseline.status = form.status;
  baseline.nodeSequence = [...form.nodeSequence];
  baseline.promptBindings = form.promptBindings.map((item) => ({ ...item }));
  baseline.strategy = { ...form.strategy };
  baseline.metadata = { ...form.metadata };
};

const resetNodePromptMap = () => {
  Object.keys(nodePromptMap).forEach((key) => delete nodePromptMap[key]);
  (form.promptBindings || []).forEach((binding) => {
    if (binding.nodeId) {
      nodePromptMap[binding.nodeId] = binding.promptId || null;
    }
  });
};

const syncPromptBindings = () => {
  form.nodeSequence = form.nodeSequence.filter(Boolean);
  updatePromptBindings();
};

const updatePromptBindings = () => {
  const bindings = form.nodeSequence.map((nodeId) => ({
    nodeId,
    promptId: nodePromptMap[nodeId] || null,
  }));
  form.promptBindings = bindings;
  emitDirty();
};

const clearPrompt = (nodeId) => {
  if (nodePromptMap[nodeId]) {
    nodePromptMap[nodeId] = null;
    updatePromptBindings();
  }
};

const resolveNodeName = (nodeId) => {
  return props.nodes.find((node) => node.id === nodeId)?.name || nodeId;
};

const validateBindings = ({ showMessage = true } = {}) => {
  const availableNodes = new Set(props.nodes.map((node) => node.id));
  const missingNodes = form.nodeSequence.filter((id) => !availableNodes.has(id));
  if (missingNodes.length) {
    form.nodeSequence = form.nodeSequence.filter((id) => availableNodes.has(id));
    missingNodes.forEach((nodeId) => {
      delete nodePromptMap[nodeId];
    });
    updatePromptBindings();
    if (showMessage) {
      ElMessage.warning("以下节点已被移除：" + missingNodes.join("、"));
    }
  }

  const availablePrompts = new Set(props.prompts.map((prompt) => prompt.id));
  const invalidBindings = Object.entries(nodePromptMap).filter(([, promptId]) => promptId && !availablePrompts.has(promptId));
  if (invalidBindings.length) {
    invalidBindings.forEach(([nodeId]) => {
      nodePromptMap[nodeId] = null;
    });
    updatePromptBindings();
    if (showMessage) {
      const nodeNames = invalidBindings.map(([nodeId]) => resolveNodeName(nodeId));
      ElMessage.warning("节点 " + nodeNames.join("、") + " 的提示词已失效，已自动清除。");
    }
  }

  if (!form.nodeSequence.length) {
    errors.nodeSequence = "请选择至少一个节点";
    return false;
  }

  errors.nodeSequence = "";
  return missingNodes.length === 0;
};

const validate = () => {
  errors.name = form.name.trim() ? "" : "名称不能为空";
  errors.nodeSequence = form.nodeSequence.length ? "" : "请选择至少一个节点";
  errors.retryLimit =
    form.strategy.retryLimit >= 0 && form.strategy.retryLimit <= 5
      ? ""
      : "重试次数需在 0-5";
  errors.timeoutMs =
    form.strategy.timeoutMs >= 0 ? "" : "超时必须大于等于 0";
  const bindingsOk = validateBindings();
  return !errors.name && !errors.nodeSequence && !errors.retryLimit && !errors.timeoutMs && bindingsOk;
};

const canSave = computed(() => {
  if (!form.name.trim()) return false;
  if (!form.nodeSequence.length) return false;
  const availableNodes = new Set(props.nodes.map((node) => node.id));
  return form.nodeSequence.every((nodeId) => availableNodes.has(nodeId));
});

const emitDirty = () => {
  const dirty = isDirty();
  emit("dirty-change", dirty);
};

const isDirty = () => {
  const sameName = form.name === baseline.name;
  const sameDesc = form.metadata.description === baseline.metadata.description;
  const sameNodes =
    form.nodeSequence.length === baseline.nodeSequence.length &&
    form.nodeSequence.every((nodeId, idx) => nodeId === baseline.nodeSequence[idx]);
  const sameBindings =
    form.promptBindings.length === baseline.promptBindings.length &&
    form.promptBindings.every((binding, idx) => {
      const ref = baseline.promptBindings[idx] || {};
      return binding.nodeId === ref.nodeId && binding.promptId === ref.promptId;
    });
  const sameStrategy =
    form.strategy.retryLimit === baseline.strategy.retryLimit &&
    form.strategy.timeoutMs === baseline.strategy.timeoutMs;
  return !(sameName && sameDesc && sameNodes && sameBindings && sameStrategy);
};

const handleSave = () => {
  if (!validate()) return;
  const payload = {
    name: form.name.trim(),
    status: form.status,
    nodeSequence: [...form.nodeSequence],
    promptBindings: form.promptBindings.map((item) => ({
      nodeId: item.nodeId,
      promptId: item.promptId,
    })),
    strategy: { ...form.strategy },
    metadata: { ...form.metadata },
  };
  emit("save", payload);
};

const handleReset = () => {
  copyIntoForm(baseline);
  emitDirty();
};

watch(
  () => props.nodes.map((node) => node.id),
  () => {
    if (form.nodeSequence.length) {
      validateBindings();
    }
  }
);

watch(
  () => props.prompts.map((prompt) => prompt.id),
  () => {
    if (form.nodeSequence.length) {
      validateBindings();
    }
  }
);

watch(
  () => props.workflow,
  (next) => {
    copyIntoForm(next || {});
    resetBaseline();
    emitDirty();
  },
  { immediate: true, deep: true }
);

watch(
  () => [form.name, form.metadata.description, form.nodeSequence, form.promptBindings, form.strategy.retryLimit, form.strategy.timeoutMs],
  () => emitDirty(),
  { deep: true }
);

defineExpose({
  isDirty,
  getPayload: () =>
    toRaw({
      name: form.name,
      status: form.status,
      nodeSequence: [...form.nodeSequence],
      promptBindings: form.promptBindings.map((item) => ({ ...item })),
      strategy: { ...form.strategy },
      metadata: { ...form.metadata },
    }),
});
</script>

<style scoped>
.workflow-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.workflow-editor__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.workflow-editor__header h2 {
  margin: 0;
}

.workflow-editor__header p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.workflow-editor__actions {
  display: flex;
  gap: var(--space-2);
}

.workflow-editor__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.workflow-editor__hint {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.workflow-editor__binding {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.workflow-editor__binding header h3 {
  margin: 0;
  font-size: var(--font-size-md);
}

.workflow-editor__binding header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.workflow-editor__binding-empty {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-align: center;
  padding: var(--space-4) 0;
}

.workflow-editor__binding-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.workflow-editor__binding-row {
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr) auto;
  gap: var(--space-2);
  align-items: center;
}

.workflow-editor__binding-label {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.workflow-editor__strategy {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.workflow-editor__strategy-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
}

@media (max-width: 720px) {
  .workflow-editor__binding-row {
    grid-template-columns: 1fr;
  }
}
</style>
