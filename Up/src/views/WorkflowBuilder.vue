<template>
  <div class="workflow-builder">
    <div v-if="canEditWorkflow" class="workflow-builder__layout">
      <div class="workflow-builder__sidebar">
        <WorkflowList
          :workflows="workflowStore.workflows"
          :selected-id="workflowStore.selectedWorkflowId"
          :loading="workflowStore.listLoading"
          @create="handleCreate"
          @select="handleSelect"
          @remove="handleDelete"
          @refresh="fetchWorkflows"
          @search="handleSearch"
        />
      </div>
      <div class="workflow-builder__content">
        <el-tabs v-model="activeTab" stretch>
          <el-tab-pane label="编辑器" name="editor">
            <WorkflowEditor
              ref="editorRef"
              :workflow="workflowStore.currentWorkflow"
              :nodes="pipelineStore.nodes"
              :prompts="promptStore.prompts"
              :saving="workflowStore.saving"
              :disabled="workflowStore.detailLoading"
              @save="handleSave"
              @dirty-change="updateDirtyState"
            />
          </el-tab-pane>
          <el-tab-pane label="发布记录" name="publish">
            <WorkflowPublishPanel
              :workflow="workflowStore.currentWorkflow"
              :history="workflowStore.history"
              :publishing="workflowStore.publishing"
              :rolling-back="workflowStore.rollingBack"
              :refreshing="workflowStore.detailLoading"
              :disabled="!workflowStore.currentWorkflow?.id"
              @publish="handlePublish"
              @rollback="handleRollback"
              @refresh="refreshCurrentWorkflow"
            />
          </el-tab-pane>
          <el-tab-pane label="渠道设置" name="channel">
            <div v-if="!isWorkflowPublished" class="workflow-builder__channel-empty">
              <el-empty description="请先发布 Workflow 才能绑定 Telegram 渠道">
                <el-button type="primary" @click="activeTab = 'publish'">前往发布</el-button>
              </el-empty>
            </div>
            <div v-else class="workflow-builder__channel">
              <WorkflowChannelForm
                ref="channelFormRef"
                :policy="channelStore.policy"
                :saving="channelStore.saving"
                :unbinding="channelStore.deleting"
                :disabled="channelStore.loading"
                :published="isWorkflowPublished"
                @save="handleChannelSave"
                @dirty-change="updateChannelDirty"
                @unbind="confirmUnbindChannel"
                @go-publish="activeTab = 'publish'"
                :coverage="channelStore.coverage"
                :coverage-loading="channelStore.coverageLoading"
                :coverage-error="channelStore.coverageError"
                :security-snapshot="channelStore.securitySnapshot"
                :security-validating="channelStore.securityChecking"
                :security-error="channelStore.securityError"
                :security-blocking-message="channelStore.securityBlockingMessage"
                @run-coverage-tests="handleRunCoverageTests"
                @validate-security="handleValidateSecurity"
              />
              <div class="workflow-builder__channel-side">
                <ChannelHealthCard
                  :health="channelStore.health"
                  :refreshing="channelStore.healthLoading"
                  :paused="healthPollingPaused"
                  :coverage="channelStore.coverage"
                  @refresh="refreshHealth"
                />
                <ChannelTestPanel
                  :workflow-id="workflowStore.currentWorkflow?.id"
                  :history="channelStore.testHistory"
                  :testing="channelStore.testing"
                  :disabled="!channelStore.isBound"
                  :cooldown-until="cooldownUntil"
                  :requires-retest="requiresSecretRetest"
                  :polling-mode="Boolean(channelStore.policy?.usePolling)"
                  @send-test="handleSendTest"
                />
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="可视化" name="canvas">
            <WorkflowCanvas
              :node-sequence="workflowStore.currentWorkflow?.nodeSequence || []"
              :nodes="pipelineStore.nodes"
              :prompt-bindings="workflowStore.currentWorkflow?.promptBindings || []"
            />
          </el-tab-pane>
          <el-tab-pane label="实时日志" name="logs">
            <div
              v-if="!observabilityEnabled"
              class="workflow-builder__placeholder"
            >
              <el-empty description="后端未启用日志接口，暂无法展示实时日志。" />
            </div>
            <WorkflowLogStream
              v-else
              :logs="visibleLogs"
              :paused="logPaused"
              :connected="logConnected"
              :retry-in="retryCountdownMs"
              :retry-message="retryMessage"
              @toggle="handleLogToggle"
              @filter-change="handleLogFilterChange"
              @export="handleLogExport"
            />
          </el-tab-pane>
          <el-tab-pane label="变量 / 工具" name="catalog">
            <div
              v-if="!observabilityEnabled"
              class="workflow-builder__placeholder"
            >
              <el-empty description="后端未启用变量/工具接口，暂无法展示。" />
            </div>
            <div v-else class="workflow-builder__catalog">
              <VariableCatalog
                :variables="variables"
                @refresh="loadVariables"
              />
              <ToolCatalog
                :tools="tools"
                @refresh="loadTools"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
    <div v-else class="workflow-builder__guard workflow-builder__guard--full">
      <el-empty :description="guardDescription">
        <div class="workflow-builder__guard-actions">
          <el-button type="primary" @click="goToNodes" :disabled="hasNodes">
            前往 Nodes
          </el-button>
          <el-button text type="primary" @click="goToPrompts" :disabled="hasPrompts">
            前往 Prompts
          </el-button>
        </div>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";

import WorkflowList from "../components/WorkflowList.vue";
import WorkflowEditor from "../components/WorkflowEditor.vue";
import WorkflowPublishPanel from "../components/WorkflowPublishPanel.vue";
import WorkflowChannelForm from "../components/WorkflowChannelForm.vue";
import ChannelHealthCard from "../components/ChannelHealthCard.vue";
import ChannelTestPanel from "../components/ChannelTestPanel.vue";
import WorkflowCanvas from "../components/WorkflowCanvas.vue";
import WorkflowLogStream from "../components/WorkflowLogStream.vue";
import VariableCatalog from "../components/VariableCatalog.vue";
import ToolCatalog from "../components/ToolCatalog.vue";
import { useWorkflowCrud } from "../composables/workflow/useWorkflowCrud";
import { useWorkflowLogs } from "../composables/workflow/useWorkflowLogs";
import { useWorkflowMeta } from "../composables/workflow/useWorkflowMeta";
import { useChannelTestGuard } from "../composables/workflow/useChannelTestGuard";

const emit = defineEmits(["navigate"]);

const crud = useWorkflowCrud({ emit });
const logs = useWorkflowLogs({
  workflowStore: crud.workflowStore,
  observabilityEnabled: crud.observabilityEnabled,
  activeTab: crud.activeTab,
});
const meta = useWorkflowMeta({
  workflowStore: crud.workflowStore,
  observabilityEnabled: crud.observabilityEnabled,
  activeTab: crud.activeTab,
});
const channel = useChannelTestGuard({
  workflowStore: crud.workflowStore,
  activeTab: crud.activeTab,
  channelDirty: crud.channelDirty,
  setChannelDirty: crud.updateChannelDirty,
});

const {
  workflowStore,
  pipelineStore,
  promptStore,
  observabilityEnabled,
  activeTab,
  hasNodes,
  hasPrompts,
  canEditWorkflow,
  guardDescription,
  isWorkflowPublished,
  fetchWorkflows,
  handleCreate,
  handleSelect,
  handleDelete,
  handleSave,
  handlePublish,
  handleRollback,
  refreshCurrentWorkflow,
  updateDirtyState,
  handleSearch,
  goToNodes,
  goToPrompts,
  updateChannelDirty,
  awaitCanLeave,
  hasSelection,
} = crud;

const {
  channelStore,
  healthPollingPaused,
  cooldownUntil,
  requiresSecretRetest,
  handleChannelSave,
  confirmUnbindChannel,
  refreshHealth,
  handleSendTest,
  handleRunCoverageTests,
  handleValidateSecurity,
} = channel;

const {
  logList,
  logPaused,
  logConnected,
  visibleLogs,
  retryCountdownMs,
  retryMessage,
  handleLogToggle,
  handleLogFilterChange,
  handleLogExport,
} = logs;

const { variables, tools, loadVariables, loadTools } = meta;

const editorRef = ref(null);
const channelFormRef = ref(null);

defineExpose({
  ensureCanLeave: awaitCanLeave,
  hasSelection,
});
</script>

<style scoped>
.workflow-builder {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
}

.workflow-builder__layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: var(--space-4);
  height: 100%;
}

.workflow-builder__sidebar,
.workflow-builder__content {
  min-height: 0;
}

.workflow-builder__content :deep(.el-tabs__content) {
  height: 100%;
  padding-top: var(--space-3);
}

.workflow-builder__content :deep(.el-tab-pane) {
  height: 100%;
}

.workflow-builder__channel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-4);
}

.workflow-builder__channel-side {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.workflow-builder__channel-empty {
  padding: var(--space-5) 0;
}

.workflow-builder__placeholder {
  padding: var(--space-5) 0;
}

.workflow-builder__guard {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) 0;
}

.workflow-builder__guard--full {
  min-height: 60vh;
}

.workflow-builder__guard-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: center;
}

.workflow-builder__catalog {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-4);
  height: 100%;
}

@media (max-width: 960px) {
  .workflow-builder__layout {
    grid-template-columns: 1fr;
  }

  .workflow-builder__channel {
    grid-template-columns: 1fr;
  }
}
</style>


