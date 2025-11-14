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
          @change="handleSequenceChange"
          data-test="workflow-node-sequence"
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

      <PromptBindingTable
        class="workflow-editor__binding"
        :node-sequence="form.nodeSequence"
        :nodes="nodes"
        :prompts="prompts"
        :node-prompt-map="nodePromptMap"
        :disabled="disabled"
        @update-binding="handlePromptBinding"
        @clear-binding="clearNodePrompt"
        @bulk-bind="handleBulkBind"
      />

      <ExecutionStrategyForm
        class="workflow-editor__strategy"
        :strategy="form.strategy"
        :errors="errors"
        :disabled="disabled"
        @update:strategy="updateStrategy"
      />
    </el-form>
  </section>
</template>

<script setup>
import ExecutionStrategyForm from "./workflow-editor/ExecutionStrategyForm.vue";
import PromptBindingTable from "./workflow-editor/PromptBindingTable.vue";
import { useWorkflowForm } from "../composables/workflow/useWorkflowForm";

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

const {
  form,
  errors,
  nodePromptMap,
  canSave,
  handleSequenceChange,
  setNodePrompt,
  clearNodePrompt,
  bulkBindPrompts,
  updateStrategy,
  handleReset: resetForm,
  handleSave: submitForm,
  isDirty,
  getPayload,
} = useWorkflowForm(props, emit);

const handleSave = () => {
  const payload = submitForm();
  if (payload) {
    emit("save", payload);
  }
};

const handleReset = () => {
  resetForm();
};

const handlePromptBinding = ({ nodeId, promptId }) => {
  setNodePrompt(nodeId, promptId);
};

const handleBulkBind = ({ nodeIds, promptId }) => {
  bulkBindPrompts(nodeIds, promptId);
};

defineExpose({
  isDirty,
  getPayload,
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

.workflow-editor__binding,
.workflow-editor__strategy {
  display: block;
}
</style>
