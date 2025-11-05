import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";

import NodeDraftForm from "../../src/components/NodeDraftForm.vue";
import { usePipelineDraftStore } from "../../src/stores/pipelineDraft";
import * as pipelineService from "../../src/services/pipelineService";

describe("NodeDraftForm", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(pipelineService, "listPipelineNodes").mockResolvedValue({ items: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("prevents saving when name is empty", async () => {
    const wrapper = mount(NodeDraftForm);

    await flushPromises();
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(wrapper.text()).toContain("节点名称不能为空");
  });

  it("saves node draft and updates store", async () => {
    const store = usePipelineDraftStore();
    vi.spyOn(pipelineService, "listPipelineNodes")
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({
        items: [
          {
            id: "node_mock",
            name: "Mock 节点",
            allowLLM: true,
            systemPrompt: "System prompt",
            createdAt: "2025-11-04T00:00:00.000Z",
          },
        ],
      });

    const createNodeDraftSpy = vi
      .spyOn(pipelineService, "createPipelineNode")
      .mockResolvedValue({
        id: "node_mock",
        name: "Mock 节点",
        allowLLM: true,
        systemPrompt: "System prompt",
        createdAt: "2025-11-04T00:00:00.000Z",
      });

    const wrapper = mount(NodeDraftForm);

    await flushPromises();
    await wrapper.find("#node-name").setValue("Mock 节点");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(createNodeDraftSpy).toHaveBeenCalledOnce();
    expect(store.nodes).toHaveLength(1);
    expect(store.nodes[0].name).toBe("Mock 节点");
  });
});
