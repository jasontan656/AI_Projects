import { describe, expect, it } from "vitest";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { mount } = require("@vue/test-utils");

import PromptBindingTable from "@up/components/workflow-editor/PromptBindingTable.vue";

const baseProps = () => ({
  nodeSequence: ["node-1", "node-2"],
  nodes: [
    { id: "node-1", name: "Node 1" },
    { id: "node-2", name: "Node 2" },
  ],
  prompts: [
    { id: "prompt-a", name: "Prompt A" },
    { id: "prompt-b", name: "Prompt B" },
  ],
  nodePromptMap: { "node-1": null, "node-2": null },
  disabled: false,
});

describe("PromptBindingTable", () => {
  it("emits update-binding when prompt changes", async () => {
    const wrapper = mount(PromptBindingTable, {
      props: baseProps(),
    });

    await wrapper.vm.handlePromptChange("node-1", "prompt-a");

    expect(wrapper.emitted()["update-binding"]).toEqual([
      [{ nodeId: "node-1", promptId: "prompt-a" }],
    ]);
  });

  it("emits clear-binding when clear is triggered", async () => {
    const wrapper = mount(PromptBindingTable, {
      props: baseProps(),
    });

    await wrapper.vm.handleClear("node-2");

    expect(wrapper.emitted()["clear-binding"]).toEqual([["node-2"]]);
  });

  it("emits bulk-bind when applyBulk is called with selections", async () => {
    const wrapper = mount(PromptBindingTable, {
      props: baseProps(),
    });

    wrapper.vm.setBulkState({
      nodeIds: ["node-1", "node-2"],
      promptId: "prompt-b",
    });
    await wrapper.vm.applyBulk();

    expect(wrapper.emitted()["bulk-bind"]).toEqual([
      [{ nodeIds: ["node-1", "node-2"], promptId: "prompt-b" }],
    ]);
  });
});
