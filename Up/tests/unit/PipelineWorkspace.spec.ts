import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../src/layouts/WorkspaceShell.vue", () => ({
  default: {
    name: "WorkspaceShellStub",
    template: '<div data-testid="workspace-shell-stub">Workspace Shell</div>',
  },
}));

import PipelineWorkspace from "../../src/views/PipelineWorkspace.vue";

describe("PipelineWorkspace", () => {
  it("renders WorkspaceShell layout wrapper", () => {
    const wrapper = mount(PipelineWorkspace);
    expect(wrapper.get('[data-testid="workspace-shell-stub"]').exists()).toBe(true);
  });
});
