<template>
  <section class="workspace-pane prompts-pane">
    <template v-if="promptStage === 'menu'">
      <PromptSubMenu :actions="promptActions" @select="handlePromptActionSelect" />
    </template>

    <template v-else-if="promptStage === 'create'">
      <div class="prompts-toolbar">
        <el-button text @click="enterPromptMenu">返回提示词菜单</el-button>
      </div>
      <div class="prompts-create">
        <PromptEditor ref="promptEditorRef" layout="full" @saved="handlePromptSaved" />
      </div>
    </template>

    <template v-else-if="promptStage === 'manage'">
      <div class="prompts-toolbar prompts-toolbar--manage">
        <el-button text @click="enterPromptMenu">返回提示词菜单</el-button>
      </div>
      <div class="workspace-pane workspace-pane--two-column prompts-manage">
        <PromptList
          class="workspace-pane__sidebar"
          @refresh="refreshPrompts"
          @delete="handleDeletePrompt"
        />
        <div class="workspace-pane__content">
          <PromptEditor ref="promptEditorRef" layout="split" @saved="handlePromptSaved" />
        </div>
      </div>
    </template>

    <template v-else>
      <el-empty description="当前阶段暂无内容" />
    </template>
  </section>
</template>

<script setup>
defineOptions({ name: "PromptsView" });

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import PromptEditor from "../../components/PromptEditor.vue";
import PromptList from "../../components/PromptList.vue";
import PromptSubMenu from "../../components/PromptSubMenu.vue";
import { usePromptDraftStore } from "../../stores/promptDraft";
import { deletePrompt } from "../../services/promptService";
import { useWorkspaceNavStore } from "../../stores/workspaceNav";

const promptStore = usePromptDraftStore();
const navStore = useWorkspaceNavStore();

const promptEditorRef = ref(null);
const promptStage = ref("menu");

const promptActions = computed(() => [
  {
    id: "create",
    label: "新建提示词",
    description: "从空白模版开始撰写 Markdown 提示词并保存为资产。",
    stage: "create",
    ctaLabel: "开始创建",
    ctaType: "primary",
  },
  {
    id: "manage",
    label: "管理提示词",
    description: "查看已保存的模板，执行编辑、删除与回滚等操作。",
    stage: "manage",
    ctaLabel: "进入管理",
    disabled: promptStore.promptCount === 0,
    reason:
      promptStore.promptCount === 0 ? "暂无提示词，请先创建一个模板。" : "",
  },
]);

const refreshPrompts = async ({ silent = false } = {}) => {
  let result;
  if (promptEditorRef.value?.refresh) {
    result = await promptEditorRef.value.refresh();
  } else {
    try {
      await promptStore.refreshPrompts();
      result = true;
    } catch (error) {
      console.warn("加载提示词失败", error);
      result = false;
    }
  }

  if (result === false) {
    if (!silent) {
      ElMessage.error("加载提示词失败，请稍后重试");
    }
    return false;
  }

  if (!promptStore.promptCount && promptStage.value === "manage") {
    await setPromptStage("menu", { force: true, skipLeaveGuard: true });
    if (!silent) {
      ElMessage.info("暂无提示词，请先创建一个模板。");
    }
  }
  return true;
};

const ensureCanLeavePromptStage = async () => {
  if (!["create", "manage"].includes(promptStage.value)) {
    return true;
  }
  const editor = promptEditorRef.value;
  const dirty = await editor?.isDirty?.();
  if (!dirty) {
    return true;
  }
  try {
    await ElMessageBox.confirm(
      "当前提示词草稿尚未保存，确定要离开吗？",
      "未保存的更改",
      {
        confirmButtonText: "仍然离开",
        cancelButtonText: "继续编辑",
        type: "warning",
      }
    );
    return true;
  } catch {
    return false;
  }
};

const applyPromptStageEntry = async (stage, meta = {}) => {
  if (stage === "menu") {
    promptStore.resetSelection();
    return;
  }
  await nextTick();
  if (stage === "create") {
    promptStore.resetSelection();
    await promptEditorRef.value?.newEntry?.();
    await promptEditorRef.value?.syncBaseline?.();
    return;
  }
  if (stage === "manage") {
    await refreshPrompts();
    if (meta?.promptId) {
      promptStore.setSelectedPrompt(meta.promptId);
    } else if (!promptStore.selectedPromptId && promptStore.prompts[0]?.id) {
      promptStore.setSelectedPrompt(promptStore.prompts[0].id);
    }
    await promptEditorRef.value?.syncBaseline?.();
  }
};

const setPromptStage = async (stage, options = {}) => {
  const { force = false, skipLeaveGuard = false, meta = {} } = options;
  if (!force && promptStage.value === stage) {
    await applyPromptStageEntry(stage, meta);
    return;
  }
  if (!skipLeaveGuard) {
    const canLeave = await ensureCanLeavePromptStage(stage);
    if (!canLeave) {
      return;
    }
  }
  promptStage.value = stage;
  await applyPromptStageEntry(stage, meta);
};

const enterPromptMenu = async () => {
  await setPromptStage("menu");
};

const startCreatePrompt = async () => {
  await setPromptStage("create");
};

const startManagePrompts = async ({ promptId } = {}) => {
  await setPromptStage("manage", { meta: { promptId } });
};

const handlePromptActionSelect = async (action) => {
  if (!action?.stage) return;
  if (action.stage === "create") {
    await startCreatePrompt();
    return;
  }
  if (action.stage === "manage") {
    await startManagePrompts();
    return;
  }
  await setPromptStage(action.stage);
};

const handlePromptSaved = async ({ promptId } = {}) => {
  await startManagePrompts({ promptId });
};

const handlePromptQuickCreate = async () => {
  if (promptStage.value === "manage") {
    promptStore.resetSelection();
    await promptEditorRef.value?.newEntry?.();
    await promptEditorRef.value?.syncBaseline?.();
  } else {
    await startCreatePrompt();
  }
};

const handleDeletePrompt = async (prompt) => {
  if (!prompt?.id) {
    return;
  }
  try {
    await ElMessageBox.confirm(
      "确认删除该提示词？该操作无法撤销。",
      "删除提示词",
      {
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
  } catch {
    return;
  }
  try {
    await deletePrompt(prompt.id);
    promptStore.removePrompt(prompt.id);
    if (promptStore.selectedPromptId === prompt.id) {
      promptStore.resetSelection();
    }
    await refreshPrompts({ silent: true });
    ElMessage.success("提示词已删除");
  } catch (error) {
    console.error("删除提示词失败", error);
    ElMessage.error("删除提示词失败，请稍后重试");
  }
};

watch(
  () => navStore.activeTab,
  async (tab) => {
    if (tab === "prompts") {
      await setPromptStage("menu", { force: true, skipLeaveGuard: true });
      await refreshPrompts({ silent: true });
    }
  }
);

const unregisterGuard = navStore.registerGuard("prompts", ensureCanLeavePromptStage);

onMounted(() => {
  promptStore.refreshPrompts().catch((error) => console.warn("加载提示词失败", error));
});

onUnmounted(() => {
  unregisterGuard();
});

defineExpose({
  resetView: () => setPromptStage("menu", { force: true, skipLeaveGuard: true }),
});
</script>

<style scoped>
.prompts-pane {
  gap: var(--space-4);
}

.prompts-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-2);
}

.prompts-toolbar .el-button {
  padding: 0;
}

.prompts-create {
  display: flex;
  justify-content: center;
}

.prompts-manage {
  align-items: stretch;
}
</style>
