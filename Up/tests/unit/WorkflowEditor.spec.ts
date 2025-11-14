import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const { mount } = require("@vue/test-utils");

import WorkflowEditor from "@up/components/WorkflowEditor.vue";

const nodes = [
  { id: "node-1", name: "Greeting" },
  { id: "node-2", name: "Follow-up" },
];

const prompts = [
  { id: "prompt-a", name: "Prompt A" },
  { id: "prompt-b", name: "Prompt B" },
];

const workflow = {
  id: "wf-1",
  name: " Demo Workflow ",
  status: "draft",
  nodeSequence: ["node-1"],
  promptBindings: [{ nodeId: "node-1", promptId: "prompt-a" }],
  strategy: { retryLimit: 3, timeoutMs: 5000 },
  metadata: { description: "desc", tags: [] },
};

const mountEditor = (override = {}) =>
  mount(WorkflowEditor, {
    props: {
      workflow,
      nodes,
      prompts,
      saving: false,
      disabled: false,
      ...override,
    },
  });

describe("WorkflowEditor", () => {
  it("emits save with sanitized payload", async () => {
    const wrapper = mountEditor();

    await wrapper.vm.handleSave();

    const saveEvent = wrapper.emitted().save?.[0]?.[0];
    expect(saveEvent).toBeDefined();
    expect(saveEvent.name).toBe("Demo Workflow");
    expect(saveEvent.nodeSequence).toEqual(["node-1"]);
    expect(saveEvent.promptBindings).toEqual([
      { nodeId: "node-1", promptId: "prompt-a" },
    ]);
  });

  it("emits dirty-change when form becomes dirty", async () => {
    const wrapper = mountEditor();

    wrapper.vm.form.name = "Changed";
    await nextTick();

    const dirtyEvents = wrapper.emitted()["dirty-change"];
    expect(dirtyEvents?.length).toBeGreaterThan(0);
    expect(dirtyEvents?.at(-1)?.[0]).toBe(true);
  });

  it("resets form to baseline", async () => {
    const wrapper = mountEditor();

    wrapper.vm.form.name = "Changed Name";
    await nextTick();
    await wrapper.vm.handleReset();

    expect(wrapper.vm.form.name).toBe(workflow.name);
    const dirtyEvents = wrapper.emitted()["dirty-change"];
    expect(dirtyEvents?.at(-1)?.[0]).toBe(false);
  });

  it("disables save when node sequence empty", async () => {
    const wrapper = mountEditor();

    wrapper.vm.form.nodeSequence = [];
    await nextTick();

    expect(wrapper.vm.canSave).toBe(false);
  });
});
