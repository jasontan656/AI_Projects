<template>
  <section :class="['prompt-editor', { 'prompt-editor--full': isFullLayout }]">
    <header class="prompt-editor__header">
      <div class="prompt-editor__title">
        <h2>{{ isEditing ? "编辑提示词" : "新增提示词" }}</h2>
        <p>编辑 MarkdownV2 内容，支持语法高亮。</p>
      </div>
      <div class="prompt-editor__actions">
        <button
          type="button"
          class="prompt-editor__primary"
          @click="handleSubmit"
          :disabled="isSaving || isOffline"
        >
          {{ isSaving ? "保存中…" : isEditing ? "更新提示词" : "保存提示词" }}
        </button>
        <span class="prompt-editor__status" :class="{ 'prompt-editor__status--visible': toastVisible }">
          {{ toastMessage }}
        </span>
      </div>
      <div
        v-if="isOffline"
        class="prompt-editor__offline"
        data-test="offline-banner"
      >
        <strong>{{ offlineCopy.primary }}</strong>
        <span>{{ offlineCopy.secondary }}</span>
      </div>
    </header>

    <div class="prompt-editor__body">
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
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";

import PromptCodeEditor from "../components/PromptCodeEditor.vue";
import { usePromptDraftStore } from "../stores/promptDraft";
import {
  createPromptDraft,
  updatePromptDraft,
} from "../services/promptService";

const props = defineProps({
  layout: {
    type: String,
    default: "split",
  },
});

const emit = defineEmits(["saved"]);

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
const baseline = reactive({ name: "", markdown: "" });

const toastMessage = ref("");
const toastVisible = ref(false);
const offlineCopy = {
  primary: "离线模式 · Offline mode",
  secondary: "请检查网络连接。Walang koneksyon, pakisuri ang iyong internet.",
};

const promptDraftStore = usePromptDraftStore();
const selectedPrompt = computed(() => promptDraftStore.selectedPrompt);
const isEditing = computed(() => Boolean(selectedPrompt.value));
const isFullLayout = computed(() => props.layout === "full");
const resolveIsOffline = () => {
  if (typeof navigator === "undefined" || typeof navigator.onLine === "undefined") {
    return false;
  }
  return navigator.onLine === false;
};
const isOffline = ref(resolveIsOffline());

const syncBaseline = () => {
  baseline.name = name.value;
  baseline.markdown = markdownContent.value;
};

const isDirty = () =>
  name.value !== baseline.name || markdownContent.value !== baseline.markdown;

const applyPrompt = (prompt) => {
  errors.name = "";
  errors.markdown = "";
  if (!prompt) {
    name.value = "";
    markdownContent.value = "";
    editorLanguage.value = "markdown";
    syncBaseline();
    return;
  }

  name.value = prompt.name || "";
  markdownContent.value = prompt.markdown || "";
  syncBaseline();
};

const fetchPrompts = async () => {
  try {
    await promptDraftStore.refreshPrompts({ pageSize: 50 });
    return true;
  } catch (error) {
    console.warn("加载提示词列表失败", error);
    return false;
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

  const trimmedName = name.value.trim();
  const trimmedMarkdown = markdownContent.value.trim();

  if (!trimmedName) {
    errors.name = "提示词名称不能为空";
    return;
  }
  if (!trimmedMarkdown) {
    errors.markdown = "Markdown 内容不能为空";
    return;
  }

  name.value = trimmedName;
  markdownContent.value = trimmedMarkdown;

  if (isOffline.value) {
    showToast("处于离线模式，无法保存。");
    return;
  }

  try {
    let targetPromptId = selectedPrompt.value?.id ?? null;
    isSaving.value = true;
    if (selectedPrompt.value) {
      await updatePromptDraft(selectedPrompt.value.id, {
        name: trimmedName,
        markdown: trimmedMarkdown,
      });
    } else {
      const created = await createPromptDraft({
        name: trimmedName,
        markdown: trimmedMarkdown,
      });
      if (created?.id) {
        promptDraftStore.setSelectedPrompt(created.id);
        targetPromptId = created.id;
      }
    }
    await fetchPrompts();
    applyPrompt(promptDraftStore.selectedPrompt || null);
    emit("saved", { promptId: targetPromptId || promptDraftStore.selectedPromptId || null });
    showToast(selectedPrompt.value ? "更新成功" : "保存成功");
    recordTelemetry("prompt_editor.save", {
      action: selectedPrompt.value ? "update" : "create",
      promptId: targetPromptId || promptDraftStore.selectedPromptId || null,
      offline: isOffline.value,
      language: editorLanguage.value,
    });
  } catch (error) {
    const message = error.message || "保存失败";
    if (message.includes("名称")) {
      errors.name = message;
    } else {
      errors.markdown = message;
    }
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

const telemetryBucketKey = "__UP_TELEMETRY__";
const recordTelemetry = (event, payload) => {
  if (typeof window === "undefined") {
    return;
  }
  const bucket = Array.isArray(window[telemetryBucketKey]) ? window[telemetryBucketKey] : [];
  bucket.push({
    event,
    payload,
    timestamp: Date.now(),
  });
  window[telemetryBucketKey] = bucket;
};

const handleOnline = () => {
  isOffline.value = false;
};

const handleOffline = () => {
  isOffline.value = true;
};

onMounted(async () => {
  if (typeof window !== "undefined") {
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
  }
  isOffline.value = resolveIsOffline();
  await fetchPrompts();
  if (!selectedPrompt.value && promptDraftStore.prompts.length) {
    promptDraftStore.setSelectedPrompt(promptDraftStore.prompts[0].id);
  }
});

onBeforeUnmount(() => {
  if (typeof window === "undefined") {
    return;
  }
  window.removeEventListener("online", handleOnline);
  window.removeEventListener("offline", handleOffline);
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

defineExpose({
  refresh: fetchPrompts,
  newEntry,
  handleSubmit,
  isDirty,
  syncBaseline,
});
</script>

<style scoped>
.prompt-editor {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
  max-width: 720px;
  margin: 0;
}

.prompt-editor--full {
  max-width: 960px;
  margin: 0 auto;
}

.prompt-editor__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.prompt-editor__title {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
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
.prompt-editor__offline {
  background: var(--color-alert-warning-bg, #fff4e5);
  border: 1px solid var(--color-alert-warning-border, #ffd8a8);
  color: var(--color-alert-warning-text, #d9480f);
  border-radius: var(--radius-xs);
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-size-xs);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.prompt-editor__primary {
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: var(--color-accent-primary);
  color: #fff;
}

.prompt-editor__primary:disabled {
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

.prompt-editor__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-panel);
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
