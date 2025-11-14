import {
  ref,
  reactive,
  computed,
  watch,
  onBeforeUnmount,
} from "vue";
import { ElMessage } from "element-plus";

import {
  subscribeWorkflowLogs,
  fetchWorkflowLogs,
} from "../../services/logService";

const LOG_LIMIT = 1000;

export function useWorkflowLogs({
  workflowStore,
  observabilityEnabled,
  activeTab,
}) {
  const logList = ref([]);
  const logPaused = ref(false);
  const logConnected = ref(false);
  const logFilters = reactive({ level: "" });
  const retryCountdownMs = ref(0);
  const retryMessage = ref("");

  let unsubscribeLogs = null;
  let retryTimer = null;
  let countdownTimer = null;
  let retryAttempt = 0;
  let streamAllowed = false;

  const visibleLogs = computed(() => {
    if (!logFilters.level) {
      return logList.value;
    }
    return logList.value.filter(
      (item) => (item.level || "").toLowerCase() === logFilters.level
    );
  });

  const appendLog = (entry) => {
    const enriched = {
      ...entry,
      timestamp: entry.timestamp || new Date().toISOString(),
      id: entry.id || `${entry.timestamp || Date.now()}-${Math.random()}`,
      level: (entry.level || "info").toLowerCase(),
    };
    logList.value = [...logList.value.slice(-LOG_LIMIT + 1), enriched];
  };

  const clearRetryState = () => {
    retryCountdownMs.value = 0;
    retryMessage.value = "";
    if (retryTimer) {
      clearTimeout(retryTimer);
      retryTimer = null;
    }
    if (countdownTimer) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  };

  const stopLogStream = () => {
    if (unsubscribeLogs) {
      unsubscribeLogs();
      unsubscribeLogs = null;
    }
    logConnected.value = false;
  };

  const startCountdown = (delayMs) => {
    retryCountdownMs.value = delayMs;
    if (countdownTimer) {
      clearInterval(countdownTimer);
    }
    countdownTimer = setInterval(() => {
      retryCountdownMs.value = Math.max(0, retryCountdownMs.value - 1000);
      if (retryCountdownMs.value === 0 && countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
      }
    }, 1000);
  };

  const scheduleRetry = (retryAfterMs) => {
    if (!streamAllowed) return;
    stopLogStream();

    let delay = retryAfterMs;
    if (typeof delay !== "number" || Number.isNaN(delay) || delay <= 0) {
      retryAttempt += 1;
      delay = Math.min(15000, 2000 * 2 ** (retryAttempt - 1));
    } else {
      retryAttempt = 0;
    }

    retryMessage.value = `日志流已断开，系统将在 ${Math.ceil(delay / 1000)} 秒后重连`;
    startCountdown(delay);

    retryTimer = setTimeout(() => {
      retryTimer = null;
      if (streamAllowed) {
        startLogStream();
      }
    }, delay);
  };

  const startLogStream = () => {
    if (
      !observabilityEnabled ||
      !streamAllowed ||
      !workflowStore.currentWorkflow?.id
    ) {
      return;
    }
    stopLogStream();
    clearRetryState();
    logConnected.value = false;
    retryAttempt = 0;
    unsubscribeLogs = subscribeWorkflowLogs(workflowStore.currentWorkflow.id, {
      onMessage: (payload) => {
        if (logPaused.value) {
          return;
        }
        logConnected.value = true;
        retryAttempt = 0;
        clearRetryState();
        appendLog(payload);
      },
      onError: () => {
        logConnected.value = false;
        scheduleRetry();
      },
      onRetry: ({ retryAfterMs }) => {
        logConnected.value = false;
        scheduleRetry(retryAfterMs);
      },
    });
  };

const setStreamState = () => {
  const shouldStream =
    observabilityEnabled &&
    activeTab.value === "logs" &&
    Boolean(workflowStore.currentWorkflow?.id);

  if (shouldStream) {
    if (!streamAllowed) {
      logList.value = [];
    }
    streamAllowed = true;
    startLogStream();
  } else {
    streamAllowed = false;
    stopLogStream();
    clearRetryState();
  }
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

  watch(
    () => [workflowStore.currentWorkflow?.id, activeTab.value],
    () => {
      setStreamState();
    },
    { immediate: true }
  );

  onBeforeUnmount(() => {
    streamAllowed = false;
    stopLogStream();
    clearRetryState();
  });

  return {
    logList,
    logPaused,
    logConnected,
    visibleLogs,
    retryCountdownMs,
    retryMessage,
    handleLogToggle,
    handleLogFilterChange,
    handleLogExport,
    startLogStream,
    stopLogStream,
  };
}
