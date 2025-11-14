import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useWorkspaceNavStore, WORKSPACE_TAB_ROUTE_MAP } from "../../src/stores/workspaceNav";

describe("workspaceNav store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("initializes with nodes tab metadata", () => {
    const store = useWorkspaceNavStore();
    expect(store.activeTab).toBe("nodes");
    expect(store.currentNav.label).toBe("Nodes");
    expect(WORKSPACE_TAB_ROUTE_MAP[store.activeTab]).toBe("WorkspaceNodes");
  });

  it("respects registered guards before navigating away", async () => {
    const store = useWorkspaceNavStore();
    const guard = vi.fn().mockResolvedValue(false);
    store.registerGuard("nodes", guard);

    const canLeave = await store.ensureCanLeave("nodes");
    expect(guard).toHaveBeenCalledTimes(1);
    expect(canLeave).toBe(false);

    guard.mockResolvedValue(true);
    const secondAttempt = await store.ensureCanLeave("nodes");
    expect(secondAttempt).toBe(true);
  });

  it("records navigation history and log connection state", () => {
    const store = useWorkspaceNavStore();
    store.recordNavigation("prompts", { reason: "test" });
    store.markLogsConnection(true);

    expect(store.navHistory).toHaveLength(1);
    expect(store.navHistory[0]).toMatchObject({ tabId: "prompts", reason: "test" });
    expect(store.logsConnected).toBe(true);

    store.$reset();
    expect(store.activeTab).toBe("nodes");
    expect(store.logsConnected).toBe(false);
    expect(store.navHistory).toHaveLength(0);
  });
});
