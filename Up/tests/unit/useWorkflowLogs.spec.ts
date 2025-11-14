import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive, ref } from "vue";

import { useWorkflowLogs } from "../../src/composables/workflow/useWorkflowLogs";
import { subscribeWorkflowLogs } from "../../src/services/logService";

const { mount, flushPromises } = require("@vue/test-utils");

const unsubscribeMock = vi.fn();
let subscribeHandlers = null;

vi.mock("../../src/services/logService", () => ({
  subscribeWorkflowLogs: vi.fn((workflowId, handlers) => {
    subscribeHandlers = handlers;
    return () => unsubscribeMock(workflowId);
  }),
  fetchWorkflowLogs: vi.fn().mockResolvedValue([]),
}));

const mountLogs = () =>
  mount({
    template: "<div />",
    setup() {
      const workflowStore = reactive({
        currentWorkflow: { id: "wf-logs" },
      });
      const activeTab = ref("logs");
      return {
        ...useWorkflowLogs({
          workflowStore,
          observabilityEnabled: true,
          activeTab,
        }),
        activeTab,
      };
    },
  });

describe("useWorkflowLogs", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    subscribeHandlers = null;
    unsubscribeMock.mockReset();
    subscribeWorkflowLogs.mockClear();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("根据 retry-after header 启动倒计时", async () => {
    const wrapper = mountLogs();
    await flushPromises();
    expect(subscribeHandlers).toBeTruthy();

    subscribeHandlers.onRetry?.({ retryAfterMs: 5000 });
    expect(wrapper.vm.retryCountdownMs).toBe(5000);

    vi.advanceTimersByTime(3000);
    expect(wrapper.vm.retryCountdownMs).toBe(2000);

    wrapper.unmount();
  });

  it("handleLogToggle 切换暂停状态", async () => {
    const wrapper = mountLogs();
    await flushPromises();

    expect(wrapper.vm.logPaused).toBe(false);
    wrapper.vm.handleLogToggle();
    expect(wrapper.vm.logPaused).toBe(true);
    wrapper.vm.handleLogToggle();
    expect(wrapper.vm.logPaused).toBe(false);

    wrapper.unmount();
  });
});
