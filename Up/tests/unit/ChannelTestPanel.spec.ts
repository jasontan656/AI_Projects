import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { mount } = require("@vue/test-utils");

import ChannelTestPanel from "../../src/components/ChannelTestPanel.vue";

const streamSpy: { lastOptions: any } = { lastOptions: null };

vi.mock("../../src/services/pipelineSseClient", () => {
  return {
    createSseStream: (options: any) => {
      streamSpy.lastOptions = options;
      return {
        start: vi.fn(),
        stop: vi.fn(),
      };
    },
  };
});

describe("ChannelTestPanel", () => {
  it("shows retest warning when requiresRetest is true", () => {
    const wrapper = mount(ChannelTestPanel, {
      props: {
        requiresRetest: true,
        cooldownUntil: 0,
      },
    });

    expect(wrapper.find('[data-test="test-panel-retest"]').exists()).toBe(true);
  });

  it("renders polling mode alert", () => {
    const wrapper = mount(ChannelTestPanel, {
      props: {
        pollingMode: true,
      },
    });

    expect(wrapper.text()).toContain("当前 workflow 通过 Polling 处理");
  });

  it("appends SSE events into history list", async () => {
    streamSpy.lastOptions = null;
    const wrapper = mount(ChannelTestPanel, {
      props: {
        workflowId: "wf-01",
      },
    });

    expect(streamSpy.lastOptions).toBeTruthy();
    streamSpy.lastOptions.onMessage({
      workflowId: "wf-01",
      status: "success",
      timestamp: "2025-11-13T12:00:00Z",
      metadata: {
        message: "覆盖测试完成",
        chatId: "12345",
        durationMs: 1500,
      },
    });

    await nextTick();

    expect(wrapper.text()).toContain("覆盖测试完成");
    expect(wrapper.text()).toContain("12345");
  });
});
