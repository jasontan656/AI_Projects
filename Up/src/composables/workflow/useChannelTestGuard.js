import { computed, watch, onBeforeUnmount } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { useChannelPolicyStore } from "../../stores/channelPolicy";

export function useChannelTestGuard({
  workflowStore,
  activeTab,
  channelDirty,
  setChannelDirty,
}) {
  const channelStore = useChannelPolicyStore();

  const isWorkflowPublished = computed(
    () => workflowStore.currentWorkflow?.status === "published"
  );

  const healthPollingPaused = computed(
    () => channelStore.healthPollingPaused
  );
  const cooldownUntil = computed(() => channelStore.cooldownUntil);
  const requiresSecretRetest = computed(() => {
    if (channelStore.securityBlockingMessage) {
      return true;
    }
    const coverageStatus = channelStore.coverage?.status || "unknown";
    if (coverageStatus !== "green" && (channelStore.policy?.secretVersion || 0) > 0) {
      return true;
    }
    return false;
  });

  const resetChannelDirty = () => {
    if (setChannelDirty) {
      setChannelDirty(false);
    }
  };

  const loadChannelIfNeeded = async () => {
    if (!workflowStore.currentWorkflow?.id || !isWorkflowPublished.value) {
      channelStore.resetPolicy();
      channelStore.stopPolling();
      resetChannelDirty();
      return;
    }
    await channelStore.fetchPolicy(workflowStore.currentWorkflow.id);
    resetChannelDirty();
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
      resetChannelDirty();
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
      resetChannelDirty();
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

  const handleRunCoverageTests = async () => {
    if (!workflowStore.currentWorkflow?.id) return;
    try {
      await channelStore.runCoverageTests(workflowStore.currentWorkflow.id, {
        scenarios:
          workflowStore.currentWorkflow?.testCoverage?.scenarios || [],
        mode: channelStore.policy?.usePolling ? "polling" : "webhook",
      });
      ElMessage.success("已触发覆盖测试");
    } catch (error) {
      ElMessage.error(error.message || "触发覆盖测试失败");
    }
  };

  const handleValidateSecurity = async (payload) => {
    if (!workflowStore.currentWorkflow?.id || !payload?.secret) {
      return;
    }
    try {
      await channelStore.validateSecretUniqueness(
        workflowStore.currentWorkflow.id,
        payload,
      );
      ElMessage.success("Secret/TLS 校验完成");
    } catch (error) {
      ElMessage.error(error.message || "Secret/TLS 校验失败");
    }
  };

  watch(
    () => workflowStore.currentWorkflow?.testCoverage,
    (coverage) => {
      channelStore.setCoverage(coverage || null);
    },
    { immediate: true }
  );

  watch(
    () => [workflowStore.currentWorkflow?.id, activeTab.value],
    () => {
      if (activeTab.value === "channel") {
        void loadChannelIfNeeded();
      } else {
        channelStore.stopPolling();
      }
    },
    { immediate: true }
  );

  onBeforeUnmount(() => {
    channelStore.stopPolling();
  });

  return {
    channelStore,
    healthPollingPaused,
    cooldownUntil,
    requiresSecretRetest,
    loadChannelIfNeeded,
    handleChannelSave,
    confirmUnbindChannel,
    refreshHealth,
    handleSendTest,
    handleRunCoverageTests,
    handleValidateSecurity,
    channelDirty,
  };
}
