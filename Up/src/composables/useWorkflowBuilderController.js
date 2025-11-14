import { useWorkflowCrud } from "./workflow/useWorkflowCrud";
import { useWorkflowLogs } from "./workflow/useWorkflowLogs";
import { useWorkflowMeta } from "./workflow/useWorkflowMeta";
import { useChannelTestGuard } from "./workflow/useChannelTestGuard";

export function useWorkflowBuilderController(options = {}) {
  const crud = useWorkflowCrud(options);
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

  return {
    ...crud,
    ...logs,
    ...meta,
    ...channel,
  };
}
