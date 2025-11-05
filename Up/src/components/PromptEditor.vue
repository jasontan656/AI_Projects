<template>
  <section class="prompt-editor">
    <header class="prompt-editor__header">
      <div>
        <h2>{{ isEditing ? "编辑提示词" : "新增提示词" }}</h2>
        <p>编辑 MarkdownV2 内容，支持语法高亮。</p>
      </div>
      <div class="prompt-editor__actions">
        <button
          type="button"
          class="prompt-editor__primary"
          @click="handleSubmit"
          :disabled="isSaving"
        >
          {{ isSaving ? "保存中…" : isEditing ? "更新提示词" : "保存提示词" }}
        </button>
        <button type="button" class="prompt-editor__ghost" @click="newEntry" :disabled="isSaving">
          新建
        </button>
        <span class="prompt-editor__status" :class="{ 'prompt-editor__status--visible': toastVisible }">
          {{ toastMessage }}
        </span>
      </div>
    </header>

    <section class="prompt-editor__form">
      <label class="prompt-editor__label" for="prompt-name">提示词名称</label>
      <input
        id="prompt-name"
        v-model="name"
        class="prompt-editor__input"
        type="text"
        placeholder="为提示词命名"
      />
      <p v-if="errors.name" class="prompt-editor__error">{{ errors.name }}</p>
    </section>

    <section class="prompt-editor__grid">
      <div class="prompt-editor__panel">
        <header class="prompt-editor__panel-header">
          <h3>内容编辑</h3>
          <div class="prompt-editor__panel-controls">
            <label class="prompt-editor__language" for="prompt-language">
              <span>语法高亮</span>
              <select
                id="prompt-language"
                name="promptLanguage"
                v-model="editorLanguage"
                class="prompt-editor__language-select"
              >
                <option v-for="option in editorLanguages" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>
        </header>
        <PromptCodeEditor
          v-model="markdownContent"
          :language="editorLanguage"
          placeholder="请输入 Markdown 正文"
        />
        <p v-if="errors.markdown" class="prompt-editor__error">{{ errors.markdown }}</p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";

import PromptCodeEditor from "../components/PromptCodeEditor.vue";
import { usePromptDraftStore } from "../stores/promptDraft";
import {
  createPromptDraft,
  listPromptDrafts,
  updatePromptDraft,
} from "../services/promptService";

const editorLanguages = [
  { label: "Markdown", value: "markdown" },
  { label: "YAML", value: "yaml" },
  { label: "JSON", value: "json" },
];

const name = ref("");
const markdownContent = ref("");
const editorLanguage = ref("markdown");
const isSaving = ref(false);
const errors = reactive({ name: "", markdown: "" });

const toastMessage = ref("");
const toastVisible = ref(false);

const promptDraftStore = usePromptDraftStore();
const selectedPrompt = computed(() => promptDraftStore.selectedPrompt);
const isEditing = computed(() => Boolean(selectedPrompt.value));

const applyPrompt = (prompt) => {
  errors.name = "";
  errors.markdown = "";
  if (!prompt) {
    name.value = "";
    markdownContent.value = "";
    editorLanguage.value = "markdown";
    return;
  }

  name.value = prompt.name || "";
  markdownContent.value = prompt.markdown || "";
};

const fetchPrompts = async () => {
  try {
    const response = await listPromptDrafts({ pageSize: 50 });
    const items = Array.isArray(response?.items) ? response.items : [];
    promptDraftStore.replacePrompts(items);
  } catch (error) {
    console.warn("加载提示词列表失败", error);
  }
};

const newEntry = () => {
  promptDraftStore.resetSelection();
  applyPrompt(null);
};

const handleSubmit = async () => {
  if (isSaving.value) return;
  errors.name = "";
  errors.markdown = "";

  if (!name.value.trim()) {
    errors.name = "提示词名称不能为空";
    return;
  }
  if (!markdownContent.value.trim()) {
    errors.markdown = "Markdown 内容不能为空";
    return;
  }

  try {
    isSaving.value = true;
    if (selectedPrompt.value) {
      await updatePromptDraft(selectedPrompt.value.id, {
        name: name.value,
        markdown: markdownContent.value,
      });
    } else {
      const created = await createPromptDraft({
        name: name.value,
        markdown: markdownContent.value,
      });
      if (created?.id) {
        promptDraftStore.setSelectedPrompt(created.id);
      }
    }
    await fetchPrompts();
    applyPrompt(promptDraftStore.selectedPrompt || null);
    showToast(selectedPrompt.value ? "更新成功" : "保存成功");
  } catch (error) {
    errors.markdown = error.message || "保存失败";
  } finally {
    isSaving.value = false;
  }
};

const showToast = (message) => {
  toastMessage.value = message;
  toastVisible.value = true;
  setTimeout(() => {
    toastVisible.value = false;
  }, 1800);
};

onMounted(async () => {
  await fetchPrompts();
  if (!selectedPrompt.value && promptDraftStore.prompts.length) {
    promptDraftStore.setSelectedPrompt(promptDraftStore.prompts[0].id);
  }
});

watch(
  selectedPrompt,
  (next) => {
    applyPrompt(next || null);
  },
  { immediate: true }
);

watch(markdownContent, () => {
  if (errors.markdown) {
    errors.markdown = "";
  }
});

watch(name, () => {
  if (errors.name) {
    errors.name = "";
  }
});

defineExpose({ refresh: fetchPrompts, newEntry, handleSubmit });
</script>

<style scoped>
.prompt-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
}

.prompt-editor__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.prompt-editor__header h2 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.prompt-editor__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.prompt-editor__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.prompt-editor__primary,
.prompt-editor__ghost {
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.prompt-editor__primary {
  background: var(--color-accent-primary);
  color: #fff;
}

.prompt-editor__ghost {
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border-subtle);
}

.prompt-editor__primary:disabled,
.prompt-editor__ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.prompt-editor__status {
  opacity: 0;
  transform: translateY(-6px);
  transition: opacity 0.3s ease, transform 0.3s ease;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.prompt-editor__status--visible {
  opacity: 1;
  transform: translateY(0);
  color: var(--color-success);
}

.prompt-editor__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.prompt-editor__label {
  font-weight: 600;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.prompt-editor__input {
  width: 100%;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xs);
  padding: var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.prompt-editor__error {
  color: #e03131;
  font-size: var(--font-size-xs);
}

.prompt-editor__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--space-3);
}

.prompt-editor__panel {
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  box-shadow: var(--shadow-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.prompt-editor__panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.prompt-editor__panel-controls {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.prompt-editor__language {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.prompt-editor__language-select {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-xs);
  background: var(--color-bg-panel);
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
  padding: var(--space-1) var(--space-2);
}

@media (max-width: 960px) {
  .prompt-editor__header {
    flex-direction: column;
    align-items: flex-start;
  }

  .prompt-editor__actions {
    align-self: flex-start;
  }

  .prompt-editor__panel-controls {
    flex-direction: column;
    align-items: flex-end;
  }
}
</style>
