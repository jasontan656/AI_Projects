import { ref, reactive, watch } from "vue";
import { ElMessage } from "element-plus";

import {
  listWorkflowVariables,
  listWorkflowTools,
} from "../../services/workflowMetaService";

export function useWorkflowMeta({
  workflowStore,
  observabilityEnabled,
  activeTab,
}) {
  const variables = ref([]);
  const tools = ref([]);
  const metaLoading = reactive({
    variables: false,
    tools: false,
  });

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

  const ensureCatalogData = async () => {
    if (
      !observabilityEnabled ||
      activeTab.value !== "catalog" ||
      !workflowStore.currentWorkflow?.id
    ) {
      return;
    }
    await Promise.all([loadVariables(), loadTools()]);
  };

  watch(
    () => [workflowStore.currentWorkflow?.id, activeTab.value],
    () => {
      void ensureCatalogData();
    },
    { immediate: true }
  );

  return {
    variables,
    tools,
    metaLoading,
    loadVariables,
    loadTools,
  };
}
