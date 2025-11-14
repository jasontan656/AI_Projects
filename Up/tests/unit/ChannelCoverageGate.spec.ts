import { createRequire } from "module";
import { describe, expect, it } from "vitest";

const require = createRequire(import.meta.url);
const { mount } = require("@vue/test-utils");

import ChannelCoverageGate from "../../src/components/channel-form/ChannelCoverageGate.vue";

const baseCoverage = {
  status: "yellow",
  updatedAt: "2025-11-13T03:10:00Z",
  scenarios: ["passport_text", "passport_attachments"],
  mode: "webhook",
  lastError: "",
};

describe("ChannelCoverageGate", () => {
  it("renders coverage status and scenarios", () => {
    const wrapper = mount(ChannelCoverageGate, {
      props: {
        coverage: baseCoverage,
      },
    });

    expect(wrapper.text()).toContain("覆盖测试");
    expect(wrapper.text()).toContain("passport_text");
    expect(wrapper.text()).toContain("passport_attachments");
  });

  it("emits run-tests when button clicked", async () => {
    const wrapper = mount(ChannelCoverageGate, {
      props: {
        coverage: baseCoverage,
      },
    });

    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("run-tests")).toBeTruthy();
  });

  it("shows blocking message when status is red", () => {
    const wrapper = mount(ChannelCoverageGate, {
      props: {
        coverage: { ...baseCoverage, status: "red" },
      },
    });
    expect(wrapper.text()).toContain("覆盖测试未通过");
  });

  it("displays polling mode notice", () => {
    const wrapper = mount(ChannelCoverageGate, {
      props: {
        coverage: { ...baseCoverage, mode: "polling" },
      },
    });
    expect(wrapper.text()).toContain("Polling 模式");
    expect(wrapper.text()).toContain("手动验证");
  });
});
