import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import PipelineWorkspace from "../../src/views/PipelineWorkspace.vue";

vi.mock("@up/services/pipelineService", () => ({
  listPipelineNodes: vi.fn().mockResolvedValue({ data: { items: [] } }),
  deletePipelineNode: vi.fn(),
}));

vi.mock("@up/services/promptService", () => ({
  listPromptDrafts: vi.fn().mockResolvedValue({ data: { items: [] } }),
  deletePrompt: vi.fn(),
}));

const NodeSubMenuStub = {
  props: ["actions"],
  emits: ["select"],
  template: `
    <div data-testid="node-sub-menu">
      <button
        v-for="action in actions"
        :key="action.id"
        :data-action="action.id"
        @click="$emit('select', action)"
        type="button"
      >
        {{ action.label }}
      </button>
    </div>
  `,
};

const PromptSubMenuStub = {
  props: ["actions"],
  emits: ["select"],
  template: `
    <div data-testid="prompt-sub-menu">
      <button
        v-for="action in actions"
        :key="action.id"
        :data-action="action.id"
        @click="$emit('select', action)"
        type="button"
      >
        {{ action.label }}
      </button>
    </div>
  `,
};

const stubComponent = (testId: string) => ({
  template: `<div data-testid="${testId}"><slot /></div>`,
});

const mountWorkspace = () =>
  mount(PipelineWorkspace, {
    global: {
      stubs: {
        NodeSubMenu: NodeSubMenuStub,
        PromptSubMenu: PromptSubMenuStub,
        NodeDraftForm: stubComponent("node-draft-form"),
        NodeList: stubComponent("node-list"),
        PromptEditor: stubComponent("prompt-editor"),
        PromptList: stubComponent("prompt-list"),
        WorkflowBuilder: stubComponent("workflow-builder"),
        VariablesPanel: stubComponent("variables-panel"),
        LogsPanel: stubComponent("logs-panel"),
        WorkflowChannelForm: stubComponent("workflow-channel-form"),
        ChannelHealthCard: stubComponent("channel-health-card"),
        ChannelTestPanel: stubComponent("channel-test-panel"),
        WorkflowCanvas: stubComponent("workflow-canvas"),
        WorkflowLogStream: stubComponent("workflow-log-stream"),
        WorkflowPublishPanel: stubComponent("workflow-publish-panel"),
        WorkflowList: stubComponent("workflow-list"),
        WorkflowEditor: stubComponent("workflow-editor"),
      },
    },
  });

describe("PipelineWorkspace", () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  test("starts in nodes menu stage and transitions to create", async () => {
    const wrapper = mountWorkspace();
    expect(wrapper.get('[data-testid="node-sub-menu"]')).toBeTruthy();

    const createButton = wrapper.get('[data-action="create"]');
    await createButton.trigger("click");

    expect(wrapper.find('[data-testid="node-sub-menu"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="node-draft-form"]').exists()).toBe(true);
  });

  test("navigates to workflow tab via side menu", async () => {
    const wrapper = mountWorkspace();
    const workflowMenu = wrapper
      .findAll('[data-testid="el-menu-item"]')
      .find((node) => node.attributes("data-index") === "workflow");
    expect(workflowMenu).toBeTruthy();
    await workflowMenu!.trigger("click");

    expect(wrapper.find('[data-testid="workflow-builder"]').exists()).toBe(true);
  });

  test("prompt actions emit menu toggle", async () => {
    const wrapper = mountWorkspace();
    const promptMenu = wrapper
      .findAll('[data-testid="el-menu-item"]')
      .find((node) => node.attributes("data-index") === "prompts");
    await promptMenu!.trigger("click");
    expect(wrapper.find('[data-testid="prompt-sub-menu"]').exists()).toBe(true);

    const createPrompt = wrapper.get('[data-testid="prompt-sub-menu"] [data-action="create"]');
    await createPrompt.trigger("click");
    expect(wrapper.find('[data-testid="prompt-editor"]').exists()).toBe(true);
  });
});
