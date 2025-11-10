<template>
  <el-container class="workspace-shell">
    <el-aside width="248px" class="workspace-aside">
      <div class="workspace-brand">
        <h1>Up Ops Workspace</h1>
        <p>Workflow configuration for LLM pipelines</p>
      </div>
      <el-menu class="workspace-menu" :default-active="activeNav">
        <el-menu-item
          index="nodes"
          @click="handleMenuClick('nodes')"
        >
          <span>Nodes</span>
        </el-menu-item>
        <el-menu-item
          v-for="item in otherNavItems"
          :key="item.id"
          :index="item.id"
          @click="handleMenuClick(item.id)"
        >
          <span>{{ item.label }}</span>
          <span v-if="item.soon" class="workspace-menu__soon">Soon</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="workspace-header">
        <div class="workspace-header__info">
          <div class="workspace-title-row">
            <h2 class="workspace-title">{{ currentNav.title }}</h2>
            <span class="workspace-section">{{ currentNav.label }}</span>
            <p class="workspace-desc">{{ currentNav.description }}</p>
          </div>
        </div>
        <div class="workspace-actions">
          <template v-if="activeNav === 'prompts'">
            <el-button
              v-if="promptStage === 'manage'"
              type="primary"
              @click="handlePromptQuickCreate"
            >
              新建提示词
            </el-button>
            <el-button
              v-else-if="promptStage === 'create'"
              text
              @click="enterPromptMenu"
            >
              返回提示词菜单
            </el-button>
          </template>
        </div>
      </el-header>

      <el-main class="workspace-main">
        <section v-if="activeNav === 'nodes'" class="workspace-pane nodes-pane">
          <template v-if="nodesStage === 'menu'">
            <NodeSubMenu :actions="nodeActions" @select="handleNodeActionSelect" />
          </template>

          <template v-else-if="nodesStage === 'create'">
            <div class="nodes-toolbar">
              <el-button text @click="enterNodesMenu">返回节点菜单</el-button>
            </div>
            <div class="nodes-create">
              <NodeDraftForm
                ref="nodeFormRef"
                layout="full"
                @saved="handleNodeSaved"
              />
            </div>
          </template>

          <template v-else-if="nodesStage === 'manage'">
            <div class="nodes-toolbar nodes-toolbar--manage">
              <el-button text @click="enterNodesMenu">返回节点菜单</el-button>
            </div>
            <div class="workspace-pane--two-column nodes-manage">
              <NodeList
                class="workspace-pane__sidebar"
                @refresh="refreshNodes"
                @delete="handleDeleteNode"
              />
              <div class="workspace-pane__content">
                <el-tabs v-model="nodesTab" class="workspace-tabs">
                  <el-tab-pane label="节点表单" name="form">
                    <NodeDraftForm
                      ref="nodeFormRef"
                      layout="split"
                      @saved="handleNodeSaved"
                    />
                  </el-tab-pane>
                  <el-tab-pane label="脚本预览（即将上线）" name="preview">
                    <el-empty
                      class="workspace-placeholder"
                      description="后续将在此提供节点动作 JSON 预览与导出。"
                    />
                  </el-tab-pane>
                </el-tabs>
              </div>
            </div>
          </template>

          <template v-else>
            <el-empty description="当前阶段未定义" />
          </template>
        </section>

        <section v-else-if="activeNav === 'prompts'" class="workspace-pane prompts-pane">
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
            <el-empty description="当前阶段未定义" />
          </template>
        </section>

        <section v-else-if="activeNav === 'workflow'" class="workspace-pane workflow-pane">
          <WorkflowBuilder ref="workflowBuilderRef" @navigate="handleWorkflowNavigate" />
        </section>

        <section v-else-if="activeNav === 'variables'" class="workspace-pane">
          <VariablesPanel />
        </section>

        <section v-else-if="activeNav === 'logs'" class="workspace-pane">
          <LogsPanel />
        </section>

        <section v-else class="workspace-pane workspace-pane--settings">
          <el-empty description="系统设置入口将在后续版本开放。" />
          <p class="workspace-pane__note">
            计划覆盖环境令牌、调试开关、导出策略等全局配置，敬请期待。
          </p>
        </section>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, nextTick, watch, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import NodeDraftForm from "../components/NodeDraftForm.vue";
import NodeList from "../components/NodeList.vue";
import PromptEditor from "../components/PromptEditor.vue";
import PromptList from "../components/PromptList.vue";
import VariablesPanel from "../components/VariablesPanel.vue";
import LogsPanel from "../components/LogsPanel.vue";
import NodeSubMenu from "../components/NodeSubMenu.vue";
import PromptSubMenu from "../components/PromptSubMenu.vue";
import WorkflowBuilder from "./WorkflowBuilder.vue";
import { usePipelineDraftStore } from "../stores/pipelineDraft";
import { usePromptDraftStore } from "../stores/promptDraft";
import { deletePipelineNode, listPipelineNodes } from "../services/pipelineService";
import { deletePrompt } from "../services/promptService";

const pipelineStore = usePipelineDraftStore();
const promptStore = usePromptDraftStore();

const nodeFormRef = ref(null);
const promptEditorRef = ref(null);
const workflowBuilderRef = ref(null);

const navItems = [
  {
    id: "nodes",
    label: "Nodes",
    title: "节点编排",
    description: "维护节点元数据与动作脚本，生成 pipeline 契约。",
  },
  {
    id: "prompts",
    label: "Prompts",
    title: "提示词模板中心",
    description: "集中管理 Markdown 模板并同步契约文件。",
  },
  {
    id: "workflow",
    label: "Workflow",
    title: "Workflow 编排",
    description: "组合节点与提示词，管理发布与回滚。",
  },
  {
    id: "variables",
    label: "Variables",
    title: "变量面板",
    description: "搜索运行时上下文，协助定位问题。",
  },
  {
    id: "logs",
    label: "Logs",
    title: "实时日志",
    description: "连接 WebSocket/SSE 查看节点执行轨迹。",
  },
  {
    id: "settings",
    label: "Settings",
    title: "工作台设置",
    description: "配置环境令牌、调试选项及 Workspace 偏好。",
    soon: true,
  },
];

const activeNav = ref("nodes");
const nodesTab = ref("form");
const nodesStage = ref("menu");
const promptStage = ref("menu");

const currentNav = computed(
  () => navItems.find((item) => item.id === activeNav.value) ?? navItems[0]
);

const otherNavItems = computed(() =>
  navItems.filter((item) => item.id !== "nodes")
);

const nodeActions = computed(() => [
  {
    id: "create",
    label: "新建节点",
    description: "从空白草稿开始构建节点配置与动作脚本。",
    stage: "create",
    ctaLabel: "开始创建",
    ctaType: "primary",
  },
  {
    id: "manage",
    label: "管理节点",
    description: "查看已创建的节点，执行编辑、删除等维护操作。",
    stage: "manage",
    ctaLabel: "进入管理",
    disabled: pipelineStore.nodeCount === 0,
    reason:
      pipelineStore.nodeCount === 0
        ? "暂无节点，请先创建一个节点后再进入管理。"
        : "",
  },
]);

const promptActions = computed(() => [
  {
    id: "create",
    label: "新建提示词",
    description: "从空白草稿开始撰写 Markdown 模板并同步契约。",
    stage: "create",
    ctaLabel: "开始创建",
    ctaType: "primary",
  },
  {
    id: "manage",
    label: "管理提示词",
    description: "查看已保存的模板，执行编辑、删除等维护操作。",
    stage: "manage",
    ctaLabel: "进入管理",
    disabled: promptStore.promptCount === 0,
    reason:
      promptStore.promptCount === 0
        ? "暂无提示词，请先创建一个模板。"
        : "",
  },
]);

const handleWorkflowNavigate = (destination) => {
  if (destination === "nodes" || destination === "prompts") {
    activeNav.value = destination;
    if (destination === "nodes") {
      nodesStage.value = "menu";
    } else {
      promptStage.value = "menu";
    }
  }
};

const primeNodes = async () => {
  try {
    const { data } = await listPipelineNodes({ pageSize: 50 });
    const items = Array.isArray(data?.items)
      ? data.items
      : Array.isArray(data)
        ? data
        : [];
    pipelineStore.replaceNodes(items);
  } catch (error) {
    console.warn("加载节点失败", error);
  }
};

const refreshNodes = async () => {
  return await nodeFormRef.value?.refresh?.();
};

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
      ElMessage.info("暂无提示词，请先创建一个提示词。");
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
      "当前提示词草稿尚未保存，确定要离开该阶段？",
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

onMounted(() => {
  primeNodes();
});

const ensureCanLeaveStage = async (targetStage) => {
  if (nodesStage.value !== "create" || targetStage === "create") {
    return true;
  }
  const dirty = nodeFormRef.value?.isDirty?.();
  if (!dirty) {
    return true;
  }
  try {
    await ElMessageBox.confirm(
      "当前节点草稿尚未保存，确定要离开该阶段？",
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

const ensureCanLeaveWorkflow = async () => {
  if (!workflowBuilderRef.value?.ensureCanLeave) {
    return true;
  }
  const result = await workflowBuilderRef.value.ensureCanLeave();
  return result !== false;
};

const applyStageEntry = async (stage, meta = {}) => {
  if (stage === "menu") {
    pipelineStore.resetSelection();
    nodesTab.value = "form";
    return;
  }
  if (stage === "create") {
    pipelineStore.resetSelection();
    nodesTab.value = "form";
    await nextTick();
    await nodeFormRef.value?.newEntry?.();
    nodeFormRef.value?.syncBaseline?.();
    return;
  }
  if (stage === "manage") {
    nodesTab.value = "form";
    await nextTick();
    await refreshNodes();
    if (!pipelineStore.nodeCount) {
      nodesStage.value = "menu";
      await applyStageEntry("menu");
      ElMessage.info("暂无节点，请先创建一个节点。");
      return;
    }
    if (meta?.nodeId) {
      pipelineStore.setSelectedNode(meta.nodeId);
    } else if (!pipelineStore.selectedNodeId && pipelineStore.nodes[0]?.id) {
      pipelineStore.setSelectedNode(pipelineStore.nodes[0].id);
    }
  }
};

const setNodesStage = async (stage, options = {}) => {
  const { force = false, skipLeaveGuard = false, meta = {} } = options;
  if (!force && nodesStage.value === stage) {
    await applyStageEntry(stage, meta);
    return;
  }
  if (!skipLeaveGuard) {
    const canLeave = await ensureCanLeaveStage(stage);
    if (!canLeave) {
      return;
    }
  }
  nodesStage.value = stage;
  await applyStageEntry(stage, meta);
};

const enterNodesMenu = async () => {
  await setNodesStage("menu");
};

const startCreateNode = async () => {
  await setNodesStage("create");
};

const startManageNodes = async ({ nodeId } = {}) => {
  await setNodesStage("manage", { meta: { nodeId } });
};

const handleNodeActionSelect = async (action) => {
  if (!action?.stage) return;
  if (action.stage === "create") {
    await startCreateNode();
    return;
  }
  if (action.stage === "manage") {
    await startManageNodes();
    return;
  }
  await setNodesStage(action.stage);
};

const handleMenuClick = async (id) => {
  if (activeNav.value === id) {
    if (id === "nodes") {
      await setNodesStage("menu", { force: true, skipLeaveGuard: true });
    } else if (id === "prompts") {
      await setPromptStage("menu", { force: true, skipLeaveGuard: true });
    }
    return;
  }

  if (activeNav.value === "nodes") {
    const canLeaveNodes = await ensureCanLeaveStage(id);
    if (!canLeaveNodes) {
      return;
    }
  }

  if (activeNav.value === "prompts") {
    const canLeavePrompts = await ensureCanLeavePromptStage();
    if (!canLeavePrompts) {
      return;
    }
  }

  if (activeNav.value === "workflow") {
    const canLeaveWorkflow = await ensureCanLeaveWorkflow();
    if (!canLeaveWorkflow) {
      return;
    }
  }

  activeNav.value = id;

  if (id === "nodes") {
    await setNodesStage("menu", { force: true, skipLeaveGuard: true });
    return;
  }

  if (id === "prompts") {
    await setPromptStage("menu", { force: true, skipLeaveGuard: true });
    return;
  }

};

const handleNodeSaved = async ({ nodeId } = {}) => {
  await startManageNodes({ nodeId });
};

watch(
  activeNav,
  async (val) => {
    if (val === "nodes") {
      await setNodesStage("menu", { force: true, skipLeaveGuard: true });
    }
    if (val === "prompts") {
      await setPromptStage("menu", { force: true, skipLeaveGuard: true });
      await refreshPrompts({ silent: true });
    }
  },
  { immediate: true }
);

const handleDeleteNode = async (node) => {
  if (!node?.id) return;
  try {
    await ElMessageBox.confirm(
      "确认删除该节点？此操作无法撤销。",
      "删除节点",
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
    await deletePipelineNode(node.id);
    pipelineStore.removeNodeDraft(node.id);
    if (pipelineStore.selectedNodeId === node.id) {
      pipelineStore.resetSelection();
    }
    await refreshNodes();
    ElMessage.success("节点已删除");
    if (!pipelineStore.nodeCount) {
      await setNodesStage("menu", { force: true, skipLeaveGuard: true });
      ElMessage.info("暂无节点，请先创建一个节点。");
    } else if (nodesStage.value === "manage" && !pipelineStore.selectedNodeId) {
      const fallbackNode = pipelineStore.nodes[0];
      if (fallbackNode?.id) {
        pipelineStore.setSelectedNode(fallbackNode.id);
      }
    }
  } catch (error) {
    console.error("删除节点失败", error);
    ElMessage.error("删除节点失败，请稍后重试");
  }
};

const handleDeletePrompt = async (prompt) => {
  if (!prompt?.id) return;
  try {
    await ElMessageBox.confirm(
      "确认删除该提示词？此操作无法撤销。",
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
    promptStore.removePromptDraft(prompt.id);
    await refreshPrompts({ silent: true });
    if (!promptStore.promptCount) {
      ElMessage.info("暂无提示词，请先创建一个提示词。");
      return;
    }
    if (promptStore.selectedPromptId === prompt.id) {
      const fallbackPrompt = promptStore.prompts[0];
      if (fallbackPrompt?.id) {
        promptStore.setSelectedPrompt(fallbackPrompt.id);
      } else {
        promptStore.resetSelection();
      }
    }
    ElMessage.success("提示词已删除");
  } catch (error) {
    console.error("删除提示词失败", error);
    ElMessage.error("删除提示词失败，请稍后重试");
  }
};
</script>

<style scoped>
.workspace-shell {
  min-height: 100vh;
  background: var(--color-bg-canvas, #f5f6fb);
}

.workspace-aside {
  position: relative;
  padding: var(--space-5) var(--space-4);
  border-right: 1px solid var(--color-border-subtle);
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.workspace-brand h1 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.workspace-brand p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-xs);
}

.workspace-menu {
  border-right: none;
}

.workspace-menu__soon {
  margin-left: var(--space-1);
  font-size: var(--font-size-2xs);
  color: var(--color-text-tertiary);
}

.workspace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-panel, #fff);
}

.workspace-header__info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.workspace-title {
  margin: 0;
  font-size: clamp(20px, 2vw, 28px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.workspace-section {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--space-2);
  height: 24px;
  border-radius: var(--radius-xs);
  background: rgba(100, 116, 139, 0.12);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-2xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.workspace-desc {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-actions {
  display: flex;
  gap: var(--space-2);
}

.workspace-main {
  padding: var(--space-5);
  background: var(--color-bg-canvas, #f5f6fb);
}

.workspace-pane {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.workspace-pane--two-column {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  align-items: stretch;
  gap: var(--space-4);
}

.workspace-pane__sidebar,
.workspace-pane__content {
  height: 100%;
  min-width: 0;
}

.workspace-tabs {
  background: transparent;
}

.workspace-placeholder {
  background: var(--color-bg-panel);
  border: 1px dashed var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-5) 0;
}

.nodes-pane {
  gap: var(--space-4);
}

.prompts-pane {
  gap: var(--space-4);
}

.nodes-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-2);
}

.nodes-toolbar .el-button {
  padding: 0;
}

.nodes-create {
  display: flex;
  justify-content: center;
}

.prompts-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: var(--space-2);
}

.prompts-toolbar .el-button {
  padding: 0;
}

.nodes-manage {
  align-items: stretch;
}

.prompts-create {
  display: flex;
  justify-content: center;
}

.prompts-manage {
  align-items: stretch;
}

.workspace-pane--settings {
  align-items: center;
  text-align: center;
}

.workspace-pane__note {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

@media (max-width: 1200px) {
  .workspace-pane--two-column {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 960px) {
  .workspace-shell {
    flex-direction: column;
  }

  .workspace-aside {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
  }

  .workspace-menu {
    flex: 1;
  }

  .workspace-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-3);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
