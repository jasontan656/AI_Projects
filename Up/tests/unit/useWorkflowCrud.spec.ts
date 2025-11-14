import { beforeEach, describe, expect, it, vi } from "vitest";
import { ElMessageBox } from "element-plus";

import { useWorkflowCrud } from "../../src/composables/workflow/useWorkflowCrud";

const { mount, flushPromises } = require("@vue/test-utils");

const workflowStoreFactory = () => ({
  fetchList: vi.fn().mockResolvedValue(undefined),
  startNewWorkflow: vi.fn(),
  selectWorkflow: vi.fn().mockResolvedValue(undefined),
  deleteWorkflow: vi.fn().mockResolvedValue(undefined),
  saveCurrentWorkflow: vi.fn().mockResolvedValue(undefined),
  publishSelected: vi.fn().mockResolvedValue(undefined),
  rollbackSelected: vi.fn().mockResolvedValue(undefined),
  loadWorkflow: vi.fn().mockResolvedValue(undefined),
  currentWorkflow: { id: "wf-001", status: "draft" },
  selectedWorkflowId: "wf-001",
  hasSelection: true,
});

const pipelineStoreFactory = () => ({
  nodeCount: 1,
  replaceNodes: vi.fn(),
});

const promptStoreFactory = () => ({
  promptCount: 1,
  replacePrompts: vi.fn(),
});

let workflowStore;
let pipelineStore;
let promptStore;

vi.mock("../../src/stores/workflowDraft", () => ({
  useWorkflowDraftStore: () => workflowStore,
}));

vi.mock("../../src/stores/pipelineDraft", () => ({
  usePipelineDraftStore: () => pipelineStore,
}));

vi.mock("../../src/stores/promptDraft", () => ({
  usePromptDraftStore: () => promptStore,
}));

vi.mock("../../src/services/pipelineService", () => ({
  listPipelineNodes: vi.fn().mockResolvedValue({ data: { items: [] } }),
}));

vi.mock("../../src/services/promptService", () => ({
  listPromptDrafts: vi.fn().mockResolvedValue({ data: { items: [] } }),
}));

const mountCrud = () =>
  mount({
    template: "<div />",
    setup() {
      return useWorkflowCrud({ emit: vi.fn() });
    },
  });

describe("useWorkflowCrud", () => {
  beforeEach(() => {
    workflowStore = workflowStoreFactory();
    pipelineStore = pipelineStoreFactory();
    promptStore = promptStoreFactory();
    ElMessageBox.confirm.mockReset();
  });

  it("阻止在未保存更改时创建新的 workflow", async () => {
    ElMessageBox.confirm.mockRejectedValueOnce(new Error("cancel"));
    const wrapper = mountCrud();
    await flushPromises();
    const api = wrapper.vm;
    api.updateDirtyState(true);

    await api.handleCreate();
    expect(workflowStore.startNewWorkflow).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("在确认后允许发布并调用 store", async () => {
    ElMessageBox.confirm.mockResolvedValueOnce(true);
    const wrapper = mountCrud();
    await flushPromises();
    const api = wrapper.vm;
    api.updateDirtyState(true);
    workflowStore.currentWorkflow = { id: "wf-002", status: "draft" };

    await api.handlePublish();
    expect(workflowStore.publishSelected).toHaveBeenCalledTimes(1);

    wrapper.unmount();
  });
});
