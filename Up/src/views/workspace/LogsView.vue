<template>
  <section class="workspace-pane logs-pane">
    <LogsPanel @connection-change="handleConnectionChange" />
  </section>
</template>

<script setup>
defineOptions({ name: "LogsView" });

import LogsPanel from "../../components/LogsPanel.vue";
import { useWorkspaceNavStore } from "../../stores/workspaceNav";
import { useWorkspaceNavigation } from "../../composables/useWorkspaceNavigation";

const navStore = useWorkspaceNavStore();
const navigation = useWorkspaceNavigation();

const handleConnectionChange = (connected) => {
  if (navigation?.markLogsConnection) {
    navigation.markLogsConnection(connected);
    return;
  }
  navStore.markLogsConnection(connected);
};

defineExpose({
  resetView: () => {},
});
</script>
