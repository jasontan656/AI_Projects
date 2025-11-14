import { ref, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { useWorkflowDraftStore } from "../../stores/workflowDraft";
import { usePipelineDraftStore } from "../../stores/pipelineDraft";
import { usePromptDraftStore } from "../../stores/promptDraft";
import { listPipelineNodes } from "../../services/pipelineService";
import { listPromptDrafts } from "../../services/promptService";

export function useWorkflowCrud({ emit } = {}) {
  const workflowStore = useWorkflowDraftStore();
  const pipelineStore = usePipelineDraftStore();
  const promptStore = usePromptDraftStore();

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
  const isWorkflowPublished = computed(
    () => workflowStore.currentWorkflow?.status === "published"
  );
  const hasSelection = computed(() => workflowStore.hasSelection);

  const activeTab = ref("editor");
  const isDirty = ref(false);
  const channelDirty = ref(false);
  const searchKeyword = ref("");

  const goToNodes = () => emit?.("navigate", "nodes");
  const goToPrompts = () => emit?.("navigate", "prompts");

  const clearWorkflowState = () => {
    workflowStore.workflows = [];
    workflowStore.startNewWorkflow();
  };

  const ensureWorkflowAccess = () => {
    if (canEditWorkflow.value) {
      return true;
    }
    ElMessage.warning(guardDescription.value);
    return false;
  };

  const fetchNodes = async () => {
    try {
      const { data } = await listPipelineNodes({ pageSize: 50 });
      const items = Array.isArray(data?.items)
        ? data.items
        : Array.isArray(data)
          ? data
          : [];
      pipelineStore.replaceNodes(items);
    } catch (error) {
      console.warn("加载节点失败", error);
    }
  };

  const fetchPrompts = async () => {
    try {
      const { data } = await listPromptDrafts({ pageSize: 50 });
      const items = Array.isArray(data?.items)
        ? data.items
        : Array.isArray(data)
          ? data
          : [];
      promptStore.replacePrompts(items);
    } catch (error) {
      console.warn("加载提示词失败", error);
    }
  };

  const fetchWorkflows = async () => {
    if (!canEditWorkflow.value) {
      clearWorkflowState();
      return;
    }
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
    if (!ensureWorkflowAccess()) return;
    if (!(await awaitCanLeave())) return;
    workflowStore.startNewWorkflow();
    activeTab.value = "editor";
  };

  const handleSelect = async (workflowId) => {
    if (!ensureWorkflowAccess()) return;
    if (!(await awaitCanLeave())) return;
    await workflowStore.selectWorkflow(workflowId);
  };

  const handleDelete = async (workflow) => {
    if (!ensureWorkflowAccess()) return;
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
    if (!ensureWorkflowAccess()) return;
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
    if (!ensureWorkflowAccess()) return;
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
    if (!ensureWorkflowAccess()) return;
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
    if (!ensureWorkflowAccess()) return;
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
    if (!ensureWorkflowAccess()) return;
    searchKeyword.value = value;
    await fetchWorkflows();
  };

  onMounted(async () => {
    await Promise.all([fetchNodes(), fetchPrompts()]);
    await fetchWorkflows();
  });

  watch(
    canEditWorkflow,
    (allowed) => {
      if (allowed) {
        void fetchWorkflows();
      } else {
        clearWorkflowState();
      }
    },
    { immediate: true }
  );

  return {
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
    hasSelection,
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
    awaitCanLeave,
    channelDirty,
    updateChannelDirty,
  };
}
