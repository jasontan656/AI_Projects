import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { flushPromises, mount } from "@vue/test-utils";

import PromptEditor from "../../src/components/PromptEditor.vue";
import { usePromptDraftStore } from "../../src/stores/promptDraft";
import * as promptService from "../../src/services/promptService";

describe("PromptEditor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders codemirror editor", async () => {
    vi.spyOn(promptService, "listPrompts").mockResolvedValue({ items: [] });
    const wrapper = mount(PromptEditor);
    await flushPromises();

    expect(wrapper.find(".prompt-editor__editor .cm-editor").exists()).toBe(true);
  });

  it("saves prompt and updates store", async () => {
    const store = usePromptDraftStore();
    vi.spyOn(promptService, "listPrompts")
      .mockResolvedValueOnce({ items: [] })
      .mockResolvedValueOnce({
        items: [
          {
            id: "prompt_mock",
            name: "新建提示词",
            markdown: "**hi**",
            createdAt: "2025-11-04T00:00:00.000Z",
            updatedAt: "2025-11-04T00:00:00.000Z",
            version: 1,
          },
        ],
      });

    const createSpy = vi
      .spyOn(promptService, "createPrompt")
      .mockResolvedValue({
        id: "prompt_mock",
        name: "新建提示词",
        markdown: "**hi**",
        createdAt: "2025-11-04T00:00:00.000Z",
        updatedAt: "2025-11-04T00:00:00.000Z",
        version: 1,
      });

    const wrapper = mount(PromptEditor);
    await flushPromises();

    const exposed = wrapper.vm.$.exposed;
    exposed.newEntry();
    wrapper.vm.name = "新建提示词";
    wrapper.vm.markdownContent = "**hi**";

    await exposed.handleSubmit();
    await flushPromises();

    expect(createSpy).toHaveBeenCalledOnce();
    expect(store.prompts).toHaveLength(1);
    expect(store.prompts[0].name).toBe("新建提示词");
  });
});
