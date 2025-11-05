import { beforeEach, describe, expect, it, vi, afterEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";

import PipelineWorkspace from "../../src/views/PipelineWorkspace.vue";
import * as pipelineService from "../../src/services/pipelineService";
import * as promptService from "../../src/services/promptService";
import { usePipelineDraftStore } from "../../src/stores/pipelineDraft";
import { usePromptDraftStore } from "../../src/stores/promptDraft";

describe("PipelineWorkspace", () => {
  let listNodesSpy;
  let listPromptsSpy;

  beforeEach(() => {
    setActivePinia(createPinia());
    listNodesSpy = vi
      .spyOn(pipelineService, "listPipelineNodes")
      .mockResolvedValue({ items: [] });
    listPromptsSpy = vi
      .spyOn(promptService, "listPrompts")
      .mockResolvedValue({ items: [] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows node form and list by default", async () => {
    const wrapper = mount(PipelineWorkspace);
    await flushPromises();

    expect(wrapper.find(".node-list").exists()).toBe(true);
    expect(wrapper.find(".node-draft").exists()).toBe(true);
  });

  it("switches to prompt editor when clicking action", async () => {
    const wrapper = mount(PipelineWorkspace);
    await flushPromises();

    await wrapper.findAll(".workspace-action")[1].trigger("click");
    await flushPromises();

    expect(wrapper.find(".prompt-list").exists()).toBe(true);
    expect(wrapper.find(".prompt-editor").exists()).toBe(true);
  });

  it("deletes a selected node when confirmed", async () => {
    const node = {
      id: "node-1",
      name: "节点1",
      allowLLM: true,
      systemPrompt: "hi",
      createdAt: "2025-01-01T00:00:00.000Z",
    };

    listNodesSpy
      .mockResolvedValueOnce({ items: [node] })
      .mockResolvedValueOnce({ items: [] });

    const deleteSpy = vi
      .spyOn(pipelineService, "deletePipelineNode")
      .mockResolvedValue({});

    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    const wrapper = mount(PipelineWorkspace);
    await flushPromises();

    await wrapper.find(".node-list__delete").trigger("click");
    await flushPromises();

    expect(confirmSpy).toHaveBeenCalled();
    expect(deleteSpy).toHaveBeenCalledWith("node-1");
    expect(usePipelineDraftStore().nodes).toHaveLength(0);
  });

  it("does not delete node when cancelled", async () => {
    const node = {
      id: "node-1",
      name: "节点1",
      allowLLM: true,
      systemPrompt: "hi",
      createdAt: "2025-01-01T00:00:00.000Z",
    };

    listNodesSpy.mockResolvedValue({ items: [node] });
    const deleteSpy = vi
      .spyOn(pipelineService, "deletePipelineNode")
      .mockResolvedValue({});

    vi.spyOn(window, "confirm").mockReturnValue(false);

    const wrapper = mount(PipelineWorkspace);
    await flushPromises();

    await wrapper.find(".node-list__delete").trigger("click");
    await flushPromises();

    expect(deleteSpy).not.toHaveBeenCalled();
    expect(usePipelineDraftStore().nodes).toHaveLength(1);
  });

  it("deletes a prompt when confirmed", async () => {
    const prompt = {
      id: "prompt-1",
      name: "提示词1",
      markdown: "**hi**",
      createdAt: "2025-01-01T00:00:00.000Z",
    };

    listPromptsSpy
      .mockResolvedValueOnce({ items: [prompt] })
      .mockResolvedValueOnce({ items: [] });

    const deleteSpy = vi
      .spyOn(promptService, "deletePrompt")
      .mockResolvedValue({});

    vi.spyOn(window, "confirm").mockReturnValue(true);

    const wrapper = mount(PipelineWorkspace);
    await flushPromises();

    await wrapper.findAll(".workspace-action")[1].trigger("click");
    await flushPromises();
    await wrapper.find(".prompt-list__delete").trigger("click");
    await flushPromises();

    expect(deleteSpy).toHaveBeenCalledWith("prompt-1");
    expect(usePromptDraftStore().prompts).toHaveLength(0);
  });
});
