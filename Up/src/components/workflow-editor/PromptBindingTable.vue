<template>
  <section class="prompt-binding-table">
    <header class="prompt-binding-table__header">
      <div>
        <h3>提示词绑定</h3>
        <p>为节点指定提示词模板，可通过批量绑定快速应用相同模板。</p>
      </div>
      <el-popover
        placement="bottom-end"
        width="320"
        trigger="click"
        v-model:visible="bulkVisible"
      >
        <template #reference>
          <el-button
            type="primary"
            link
            size="small"
            :disabled="!hasNodes || disabled"
            data-test="binding-bulk-button"
            @click="openBulk"
          >
            批量绑定
          </el-button>
        </template>
        <div class="prompt-binding-table__bulk" data-test="binding-bulk-panel">
          <el-select
            v-model="bulkPromptId"
            placeholder="选择提示词"
            filterable
            class="prompt-binding-table__bulk-input"
            :disabled="disabled"
            data-test="binding-bulk-prompt"
          >
            <el-option
              v-for="prompt in prompts"
              :key="prompt.id"
              :label="prompt.name || '(未命名提示词)'"
              :value="prompt.id"
            />
          </el-select>
          <el-select
            v-model="bulkNodeIds"
            placeholder="选择节点"
            multiple
            filterable
            class="prompt-binding-table__bulk-input"
            :disabled="disabled"
            data-test="binding-bulk-nodes"
          >
            <el-option
              v-for="nodeId in nodeSequence"
              :key="nodeId"
              :label="resolveNodeName(nodeId)"
              :value="nodeId"
            />
          </el-select>
          <div class="prompt-binding-table__bulk-actions">
            <el-button
              text
              size="small"
              data-test="binding-bulk-cancel"
              @click="bulkVisible = false"
            >
              取消
            </el-button>
            <el-button
              type="primary"
              size="small"
              :disabled="!canBulkApply || disabled"
              data-test="binding-bulk-apply"
              @click="applyBulk"
            >
              应用
            </el-button>
          </div>
        </div>
      </el-popover>
    </header>

    <div
      v-if="!hasNodes"
      class="prompt-binding-table__empty"
      data-test="binding-empty"
    >
      请选择节点后再配置提示词。
    </div>
    <div v-else class="prompt-binding-table__grid">
      <div
        v-for="nodeId in nodeSequence"
        :key="nodeId"
        class="prompt-binding-table__row"
      >
        <div class="prompt-binding-table__label">
          {{ resolveNodeName(nodeId) }}
        </div>
        <el-select
          class="prompt-binding-table__select"
          :model-value="nodePromptMap[nodeId] || null"
          filterable
          clearable
          placeholder="可选提示词"
          :disabled="disabled"
          data-test="binding-select"
          @change="(value) => handlePromptChange(nodeId, value)"
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
          :disabled="disabled"
          data-test="binding-clear"
          @click="() => handleClear(nodeId)"
        >
          清除
        </el-button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  nodeSequence: {
    type: Array,
    default: () => [],
  },
  nodes: {
    type: Array,
    default: () => [],
  },
  prompts: {
    type: Array,
    default: () => [],
  },
  nodePromptMap: {
    type: Object,
    default: () => ({}),
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update-binding", "clear-binding", "bulk-bind"]);

const bulkVisible = ref(false);
const bulkPromptId = ref(null);
const bulkNodeIds = ref([]);

const hasNodes = computed(() => props.nodeSequence.length > 0);
const canBulkApply = computed(
  () => hasNodes.value && !!bulkPromptId.value && bulkNodeIds.value.length > 0,
);

const resolveNodeName = (nodeId) =>
  props.nodes.find((node) => node.id === nodeId)?.name || "(未命名节点)";

const handlePromptChange = (nodeId, promptId) => {
  emit("update-binding", { nodeId, promptId });
};

const handleClear = (nodeId) => {
  emit("clear-binding", nodeId);
};

const openBulk = () => {
  bulkNodeIds.value = [...props.nodeSequence];
  bulkPromptId.value = null;
};

const setBulkState = ({ nodeIds = [], promptId = null } = {}) => {
  bulkNodeIds.value = [...nodeIds];
  bulkPromptId.value = promptId;
};

const applyBulk = () => {
  if (!canBulkApply.value) return;
  emit("bulk-bind", {
    nodeIds: [...bulkNodeIds.value],
    promptId: bulkPromptId.value,
  });
  bulkVisible.value = false;
  bulkNodeIds.value = [];
  bulkPromptId.value = null;
};

defineExpose({
  handlePromptChange,
  handleClear,
  setBulkState,
  applyBulk,
});
</script>

<style scoped>
.prompt-binding-table {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.prompt-binding-table__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
  align-items: center;
}

.prompt-binding-table__header h3 {
  margin: 0;
  font-size: 1rem;
}

.prompt-binding-table__header p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 0.875rem;
}

.prompt-binding-table__empty {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: var(--space-3);
  color: var(--el-text-color-secondary);
  text-align: center;
}

.prompt-binding-table__grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.prompt-binding-table__row {
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  gap: var(--space-2);
  align-items: center;
}

.prompt-binding-table__label {
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.prompt-binding-table__select {
  width: 100%;
}

.prompt-binding-table__bulk {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.prompt-binding-table__bulk-input {
  width: 100%;
}

.prompt-binding-table__bulk-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-1);
}
@media (max-width: 960px) {
  .prompt-binding-table__row {
    grid-template-columns: 1fr;
  }
}
</style>
