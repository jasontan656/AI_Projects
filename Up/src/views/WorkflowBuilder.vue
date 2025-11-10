<template>
  <div class="workflow-builder">
    <div class="workflow-builder__layout">
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
            <div
              v-if="!canEditWorkflow"
              class="workflow-builder__guard"
            >
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
            <WorkflowEditor
              v-else
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
              />
              <div class="workflow-builder__channel-side">
                <ChannelHealthCard
                  :health="channelStore.health"
                  :refreshing="channelStore.healthLoading"
                  :paused="healthPollingPaused"
                  @refresh="refreshHealth"
                />
                <ChannelTestPanel
                  :history="channelStore.testHistory"
                  :testing="channelStore.testing"
                  :disabled="!channelStore.isBound"
                  :cooldown-until="cooldownUntil"
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
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, watch, ref, reactive } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

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
import { useWorkflowDraftStore } from "../stores/workflowDraft";
import { usePipelineDraftStore } from "../stores/pipelineDraft";
import { usePromptDraftStore } from "../stores/promptDraft";
import { useChannelPolicyStore } from "../stores/channelPolicy";
import { listPipelineNodes } from "../services/pipelineService";
import { listPromptDrafts } from "../services/promptService";
import { subscribeWorkflowLogs, fetchWorkflowLogs } from "../services/logService";
import {
  listWorkflowVariables,
  listWorkflowTools,
} from "../services/workflowMetaService";

const emit = defineEmits(["navigate"]);
const workflowStore = useWorkflowDraftStore();
const pipelineStore = usePipelineDraftStore();
const promptStore = usePromptDraftStore();
const channelStore = useChannelPolicyStore();
const observabilityEnabled =
  (import.meta.env.VITE_ENABLE_OBSERVABILITY || "").toLowerCase() === "true";

const hasNodes = computed(() => pipelineStore.nodeCount > 0);
const hasPrompts = computed(() => promptStore.promptCount > 0);
const canEditWorkflow = computed(() => hasNodes.value && hasPrompts.value);
const guardDescription = computed(() => {
  if (!hasNodes.value && !hasPrompts.value) {
    return "请先创建节点和提示词，再回到 Workflow";
  }
  if (!hasNodes.value) {
    return "Workflow 需要至少 1 个节点";
  }
  return "Workflow 需要至少 1 个提示词";
});

const activeTab = ref("editor");
const editorRef = ref(null);
const channelFormRef = ref(null);
const isDirty = ref(false);
const channelDirty = ref(false);
const searchKeyword = ref("");
const logList = ref([]);
const logPaused = ref(false);
const logConnected = ref(false);
const logFilters = reactive({ level: "" });
let unsubscribeLogs = null;
let logRetryCount = 0;
let logRetryTimer = null;
const LOG_LIMIT = 1000;
const variables = ref([]);
const tools = ref([]);
const metaLoading = reactive({ variables: false, tools: false });

const hasSelection = computed(() => workflowStore.hasSelection);
const isWorkflowPublished = computed(
  () => workflowStore.currentWorkflow?.status === "published"
);
const healthPollingPaused = computed(
  () => channelStore.failureCount >= 3 && Boolean(channelStore.healthError)
);
const cooldownUntil = computed(() => {
  if (channelStore.frequencyWindow.length < 3) {
    return 0;
  }
  const oldest = channelStore.frequencyWindow[0];
  return oldest + 60000;
});
const visibleLogs = computed(() => {
  if (!logFilters.level) {
    return logList.value;
  }
  return logList.value.filter(
    (item) => (item.level || "").toLowerCase() === logFilters.level
  );
});

const goToNodes = () => emit("navigate", "nodes");
const goToPrompts = () => emit("navigate", "prompts");


const fetchNodes = async () => {
  try {
    const { data } = await listPipelineNodes({ pageSize: 50 });
    const items = Array.isArray(data?.items) ? data.items : [];
    pipelineStore.replaceNodes(items);
  } catch (error) {
    console.warn("加载节点失败", error);
  }
};

const fetchPrompts = async () => {
  try {
    const { data } = await listPromptDrafts({ pageSize: 50 });
    const items = Array.isArray(data?.items) ? data.items : [];
    promptStore.replacePrompts(items);
  } catch (error) {
    console.warn("加载提示词失败", error);
  }
};

const fetchWorkflows = async () => {
  await workflowStore.fetchList({
    search: searchKeyword.value || undefined,
  });
};

const handleCreate = async () => {
  if (!(await awaitCanLeave())) return;
  workflowStore.startNewWorkflow();
  activeTab.value = "editor";
};

const handleSelect = async (workflowId) => {
  if (!(await awaitCanLeave())) return;
  await workflowStore.selectWorkflow(workflowId);
};

const handleDelete = async (workflow) => {
  if (!workflow?.id) return;
  if (workflow.status === "published") {
    ElMessage.warning("已发布 workflow 需先回滚/解绑渠道后再删除");
    return;
  }
  try {
    await workflowStore.deleteWorkflow(workflow.id);
    ElMessage.success("已删除 Workflow");
  } catch (error) {
    ElMessage.error(error.message || "删除失败");
  }
};

const handleSave = async (payload) => {
  try {
    await workflowStore.saveCurrentWorkflow(payload);
    ElMessage.success("Workflow 已保存");
    resetDirty();
    await workflowStore.loadWorkflow(workflowStore.selectedWorkflowId);
  } catch (error) {
    ElMessage.error(error.message || "保存失败");
  }
};

const handlePublish = async () => {
  if (!workflowStore.currentWorkflow?.id) return;
  if (isDirty.value) {
    const confirmDirty = await confirmLeave(
      "当前 workflow 存在未保存的更改，发布前请保存或放弃。"
    );
    if (!confirmDirty) {
      return;
    }
  }
  try {
    await workflowStore.publishSelected({});
    ElMessage.success("发布成功");
    await workflowStore.loadWorkflow(workflowStore.selectedWorkflowId);
  } catch (error) {
    ElMessage.error(error.message || "发布失败");
  }
};

const handleRollback = async (version) => {
  if (version === undefined || version === null) return;
  try {
    await ElMessageBox.confirm(
      `确认回滚到版本 v${version}？`,
      "回滚版本",
      {
        type: "warning",
        confirmButtonText: "回滚",
        cancelButtonText: "取消",
      }
    );
  } catch {
    return;
  }
  try {
    await workflowStore.rollbackSelected(version);
    ElMessage.success(`已回滚到 v${version}`);
  } catch (error) {
    ElMessage.error(error.message || "回滚失败");
  }
};

const refreshCurrentWorkflow = async () => {
  if (!workflowStore.selectedWorkflowId) return;
  await workflowStore.loadWorkflow(workflowStore.selectedWorkflowId);
};

const awaitCanLeave = async () => {
  if (isDirty.value || channelDirty.value) {
    return confirmLeave("当前 workflow 或渠道设置存在未保存的更改，确定要放弃吗？");
  }
  return true;
};

const confirmLeave = async (message) => {
  try {
    await ElMessageBox.confirm(message, "未保存更改", {
      type: "warning",
      confirmButtonText: "仍然离开",
      cancelButtonText: "继续编辑",
    });
    return true;
  } catch {
    return false;
  }
};

const updateDirtyState = (dirty) => {
  isDirty.value = dirty;
};

const resetDirty = () => {
  isDirty.value = false;
};

const handleSearch = async (value) => {
  searchKeyword.value = value;
  await fetchWorkflows();
};

const loadChannelIfNeeded = async () => {
  if (!workflowStore.currentWorkflow?.id || !isWorkflowPublished.value) {
    channelStore.resetPolicy();
    channelStore.stopPolling();
    channelDirty.value = false;
    return;
  }
  await channelStore.fetchPolicy(workflowStore.currentWorkflow.id);
  channelDirty.value = false;
  await channelStore.fetchHealth(workflowStore.currentWorkflow.id);
};

const refreshHealth = async () => {
  if (!workflowStore.currentWorkflow?.id) return;
  await channelStore.fetchHealth(workflowStore.currentWorkflow.id, {
    silent: false,
  });
};

const handleChannelSave = async (payload) => {
  if (!workflowStore.currentWorkflow?.id) return;
  try {
    await channelStore.savePolicy(workflowStore.currentWorkflow.id, payload);
    channelDirty.value = false;
    ElMessage.success("渠道配置已保存");
    await refreshHealth();
  } catch (error) {
    ElMessage.error(error.message || "保存渠道配置失败");
  }
};

const confirmUnbindChannel = async () => {
  if (!workflowStore.currentWorkflow?.id) return;
  try {
    await ElMessageBox.confirm(
      "解绑后 Telegram Bot 将无法响应该 Workflow，确定操作？",
      "解绑渠道",
      {
        type: "warning",
        confirmButtonText: "解绑",
        cancelButtonText: "取消",
      }
    );
  } catch {
    return;
  }
  try {
    await channelStore.removePolicy(workflowStore.currentWorkflow.id);
    channelDirty.value = false;
    channelStore.stopPolling();
    ElMessage.success("已解绑 Telegram 渠道");
  } catch (error) {
    ElMessage.error(error.message || "解绑失败");
  }
};

const handleSendTest = async (payload) => {
  if (!workflowStore.currentWorkflow?.id) return;
  try {
    await channelStore.sendTest({
      workflowId: workflowStore.currentWorkflow.id,
      ...payload,
    });
    ElMessage.success("测试消息已发送");
  } catch (error) {
    ElMessage.error(error.message || "测试失败");
  }
};

const updateChannelDirty = (dirty) => {
  channelDirty.value = dirty;
};

const appendLog = (entry) => {
  const enriched = {
    ...entry,
    timestamp: entry.timestamp || new Date().toISOString(),
    id: entry.id || `${entry.timestamp || Date.now()}-${Math.random()}`,
    level: (entry.level || "info").toLowerCase(),
  };
  logList.value = [...logList.value.slice(-LOG_LIMIT + 1), enriched];
};

const startLogStream = () => {
  if (!observabilityEnabled) return;
  stopLogStream();
  if (!workflowStore.currentWorkflow?.id) return;
  unsubscribeLogs = subscribeWorkflowLogs(workflowStore.currentWorkflow.id, {
    onMessage: (payload) => {
      logConnected.value = true;
      logRetryCount = 0;
      appendLog(payload);
    },
    onError: () => {
      logConnected.value = false;
      scheduleLogRetry();
    },
  });
};

const stopLogStream = () => {
  if (unsubscribeLogs) {
    unsubscribeLogs();
    unsubscribeLogs = null;
  }
  if (logRetryTimer) {
    clearTimeout(logRetryTimer);
    logRetryTimer = null;
  }
};

const scheduleLogRetry = () => {
  if (!observabilityEnabled) return;
  stopLogStream();
  if (!workflowStore.currentWorkflow?.id) return;
  logRetryCount += 1;
  const delay = Math.min(15000, 2000 * 2 ** (logRetryCount - 1));
  logRetryTimer = setTimeout(() => {
    startLogStream();
  }, delay);
};

const handleLogToggle = () => {
  if (!observabilityEnabled) return;
  logPaused.value = !logPaused.value;
};

const handleLogFilterChange = (filters) => {
  logFilters.level = filters.level || "";
};

const handleLogExport = async () => {
  if (!observabilityEnabled || !workflowStore.currentWorkflow?.id) return;
  try {
    const data = await fetchWorkflowLogs(workflowStore.currentWorkflow.id, {
      limit: 200,
      level: logFilters.level || undefined,
    });
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `workflow-${workflowStore.currentWorkflow.id}-logs-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    ElMessage.error(error.message || "导出失败");
  }
};

const loadVariables = async () => {
  if (!observabilityEnabled || !workflowStore.currentWorkflow?.id) return;
  metaLoading.variables = true;
  try {
    variables.value = await listWorkflowVariables(
      workflowStore.currentWorkflow.id
    );
  } catch (error) {
    ElMessage.error(error.message || "加载变量失败");
  } finally {
    metaLoading.variables = false;
  }
};

const loadTools = async () => {
  if (!observabilityEnabled || !workflowStore.currentWorkflow?.id) return;
  metaLoading.tools = true;
  try {
    tools.value = await listWorkflowTools(workflowStore.currentWorkflow.id);
  } catch (error) {
    ElMessage.error(error.message || "加载工具失败");
  } finally {
    metaLoading.tools = false;
  }
};

onMounted(async () => {
  await Promise.all([fetchNodes(), fetchPrompts()]);
  await fetchWorkflows();
});

watch(
  () => workflowStore.currentWorkflow?.id,
  async () => {
    if (activeTab.value === "channel") {
      await loadChannelIfNeeded();
    } else {
      channelStore.stopPolling();
    }
    if (observabilityEnabled && activeTab.value === "logs") {
      logList.value = [];
      logRetryCount = 0;
      startLogStream();
    } else if (observabilityEnabled) {
      stopLogStream();
    }
    if (observabilityEnabled && activeTab.value === "catalog") {
      await Promise.all([loadVariables(), loadTools()]);
    }
  }
);

watch(
  () => activeTab.value,
  async (tab) => {
    if (tab === "channel") {
      await loadChannelIfNeeded();
    } else {
      channelStore.stopPolling();
    }
    if (observabilityEnabled && tab === "logs") {
      logList.value = [];
      logRetryCount = 0;
      startLogStream();
    } else if (observabilityEnabled) {
      stopLogStream();
    }
    if (observabilityEnabled && tab === "catalog") {
      await Promise.all([loadVariables(), loadTools()]);
    }
  }
);

onBeforeUnmount(() => {
  channelStore.stopPolling();
  stopLogStream();
});

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


