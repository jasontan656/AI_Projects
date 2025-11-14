<template>
  <section class="workspace-pane workflow-pane">
    <WorkflowBuilder ref="workflowBuilderRef" @navigate="handleWorkflowNavigate" />
  </section>
</template>

<script setup>
defineOptions({ name: "WorkflowView" });

import { onUnmounted, ref } from "vue";

import WorkflowBuilder from "../WorkflowBuilder.vue";
import { useWorkspaceNavStore } from "../../stores/workspaceNav";
import { useWorkspaceNavigation } from "../../composables/useWorkspaceNavigation";

const workflowBuilderRef = ref(null);
const navStore = useWorkspaceNavStore();
const navigation = useWorkspaceNavigation();

const ensureCanLeaveWorkflow = async () => {
  if (!workflowBuilderRef.value?.ensureCanLeave) {
    return true;
  }
  const result = await workflowBuilderRef.value.ensureCanLeave();
  return result !== false;
};

const unregisterGuard = navStore.registerGuard("workflow", ensureCanLeaveWorkflow);

const handleWorkflowNavigate = (destination) => {
  if (!destination || !navigation?.navigate) {
    return;
  }
  navigation.navigate(destination, { reason: "workflow-navigate" });
};

onUnmounted(() => {
  unregisterGuard();
});

defineExpose({
  resetView: () => workflowBuilderRef.value?.resetView?.(),
});
</script>
