import {
  ref,
  reactive,
  computed,
  watch,
  onMounted,
  onBeforeUnmount,
} from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

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

const LOG_LIMIT = 1000;

export function useWorkflowBuilderController({ emit } = {}) {
  const workflowStore = useWorkflowDraftStore();
  const pipelineStore = usePipelineDraftStore();
  const promptStore = usePromptDraftStore();
  const channelStore = useChannelPolicyStore();
  const observabilityEnabled =
    (import.meta.env.VITE_ENABLE_OBSERVABILITY || "")
      .toLowerCase() === "true";

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
  const isWorkflowPublished = computed(
    () => workflowStore.currentWorkflow?.status === "published"
  );
  const healthPollingPaused = computed(
    () => channelStore.healthPollingPaused
  );
  const cooldownUntil = computed(() => channelStore.cooldownUntil);

  const activeTab = ref("editor");
  const isDirty = ref(false);
  const channelDirty = ref(false);
  const searchKeyword = ref("");
  const logList = ref([]);
  const logPaused = ref(false);
  const logConnected = ref(false);
  const logFilters = reactive({ level: "" });
  const variables = ref([]);
  const tools = ref([]);
  const metaLoading = reactive({ variables: false, tools: false });

  let unsubscribeLogs = null;
  let logRetryCount = 0;
  let logRetryTimer = null;

  const visibleLogs = computed(() => {
    if (!logFilters.level) {
      return logList.value;
    }
    return logList.value.filter(
      (item) => (item.level || "").toLowerCase() === logFilters.level
    );
  });

  const goToNodes = () => emit?.("navigate", "nodes");
  const goToPrompts = () => emit?.("navigate", "prompts");

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

  const awaitCanLeave = async () => {
    if (isDirty.value || channelDirty.value) {
      return confirmLeave("当前 workflow 或渠道设置存在未保存的更改，确定要放弃吗？");
    }
    return true;
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
      isDirty.value = false;
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
      await ElMessageBox.confirm(`确认回滚到版本 v${version}？`, "回滚版本", {
        type: "warning",
        confirmButtonText: "回滚",
        cancelButtonText: "取消",
      });
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

  const updateDirtyState = (dirty) => {
    isDirty.value = dirty;
  };

  const updateChannelDirty = (dirty) => {
    channelDirty.value = dirty;
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

  const appendLog = (entry) => {
    const enriched = {
      ...entry,
      timestamp: entry.timestamp || new Date().toISOString(),
      id: entry.id || `${entry.timestamp || Date.now()}-${Math.random()}`,
      level: (entry.level || "info").toLowerCase(),
    };
    logList.value = [...logList.value.slice(-LOG_LIMIT + 1), enriched];
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

  const startLogStream = () => {
    if (!observabilityEnabled) return;
    stopLogStream();
    if (!workflowStore.currentWorkflow?.id) return;
    logConnected.value = false;
    logRetryCount = 0;
    unsubscribeLogs = subscribeWorkflowLogs(workflowStore.currentWorkflow.id, {
      onMessage: (payload) => {
        if (logPaused.value) {
          return;
        }
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

  const handleWorkflowChange = async () => {
    if (activeTab.value === "channel") {
      await loadChannelIfNeeded();
    } else {
      channelStore.stopPolling();
    }
    if (observabilityEnabled && activeTab.value === "logs") {
      logList.value = [];
      startLogStream();
    } else if (observabilityEnabled) {
      stopLogStream();
    }
    if (observabilityEnabled && activeTab.value === "catalog") {
      await Promise.all([loadVariables(), loadTools()]);
    }
  };

  const handleTabChange = async (tab) => {
    if (tab === "channel") {
      await loadChannelIfNeeded();
    } else {
      channelStore.stopPolling();
    }
    if (observabilityEnabled && tab === "logs") {
      logList.value = [];
      startLogStream();
    } else if (observabilityEnabled) {
      stopLogStream();
    }
    if (observabilityEnabled && tab === "catalog") {
      await Promise.all([loadVariables(), loadTools()]);
    }
  };

  onMounted(async () => {
    await Promise.all([fetchNodes(), fetchPrompts()]);
    await fetchWorkflows();
  });

  onBeforeUnmount(() => {
    channelStore.stopPolling();
    stopLogStream();
  });

  watch(
    () => workflowStore.currentWorkflow?.id,
    () => {
      void handleWorkflowChange();
    }
  );

  watch(
    () => activeTab.value,
    (tab) => {
      void handleTabChange(tab);
    }
  );

  return {
    workflowStore,
    pipelineStore,
    promptStore,
    channelStore,
    observabilityEnabled,
    activeTab,
    hasNodes,
    hasPrompts,
    canEditWorkflow,
    guardDescription,
    isWorkflowPublished,
    healthPollingPaused,
    cooldownUntil,
    logList,
    logPaused,
    logConnected,
    visibleLogs,
    variables,
    tools,
    metaLoading,
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
    loadChannelIfNeeded,
    handleChannelSave,
    updateChannelDirty,
    confirmUnbindChannel,
    refreshHealth,
    handleSendTest,
    handleLogToggle,
    handleLogFilterChange,
    handleLogExport,
    loadVariables,
    loadTools,
    awaitCanLeave,
    hasSelection,
  };
}
