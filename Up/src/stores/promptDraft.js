import { defineStore } from "pinia";

import { listPromptDrafts } from "../services/promptService";

const createInitialState = () => ({
  prompts: [],
  selectedPromptId: null,
});

export const usePromptDraftStore = defineStore("promptDraft", {
  state: () => createInitialState(),
  getters: {
    promptCount: (state) => state.prompts.length,
    selectedPrompt: (state) =>
      state.prompts.find((item) => item.id === state.selectedPromptId) || null,
  },
  actions: {
    replacePrompts(prompts = []) {
      this.prompts = prompts.map((item) => ({ ...item }));
      if (this.selectedPromptId) {
        const exists = this.prompts.some(
          (item) => item.id === this.selectedPromptId
        );
        if (!exists) {
          this.selectedPromptId = null;
        }
      }
    },
    addPromptDraft(prompt) {
      if (!prompt || !prompt.id) {
        throw new Error("Invalid prompt payload: missing id");
      }
      const exists = this.prompts.some((item) => item.id === prompt.id);
      if (exists) {
        this.prompts = this.prompts.map((item) =>
          item.id === prompt.id ? { ...item, ...prompt } : item
        );
        return;
      }
      this.prompts.push({ ...prompt });
    },
    removePromptDraft(id) {
      this.prompts = this.prompts.filter((item) => item.id !== id);
      if (this.selectedPromptId === id) {
        this.selectedPromptId = null;
      }
    },
    setSelectedPrompt(id) {
      this.selectedPromptId = id;
    },
    resetSelection() {
      this.selectedPromptId = null;
    },
    reset() {
      this.$reset();
    },
    async refreshPrompts(options = {}) {
      const page = options.page ?? 1;
      const pageSize = options.pageSize ?? 50;
      const { data } = await listPromptDrafts({ page, pageSize });
      const items = Array.isArray(data?.items) ? data.items : [];
      this.replacePrompts(items);
      return items;
    },
  },
});
