<template>
  <el-container class="workspace-shell">
    <el-aside ref="workspaceAside" width="248px" class="workspace-aside">
      <div class="workspace-brand">
        <h1>Up Ops Workspace</h1>
        <p>Workflow configuration for LLM pipelines</p>
      </div>
      <el-menu class="workspace-menu" :default-active="activeNav">
        <el-menu-item
          index="nodes"
          ref="nodesMenuRef"
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
      <transition name="fade">
        <div
          v-if="nodesMenuVisible"
          ref="nodesMenuPopover"
          class="nodes-submenu-pop"
          :style="{ top: `${nodesMenuPosition}px` }"
        >
          <NodeSubMenu @create="openCreateFromMenu" @manage="openManageFromMenu" />
        </div>
      </transition>
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
          <el-button
            v-if="activeNav === 'prompts'"
            type="primary"
            @click="handlePrimaryAction"
          >
            新建提示词
          </el-button>
        </div>
      </el-header>

      <el-main class="workspace-main">
        <section v-if="activeNav === 'nodes'" class="workspace-pane nodes-pane">
          <template v-if="nodesViewMode === 'create'">
            <div class="nodes-toolbar">
              <el-button type="text" @click="enterNodesMenu">返回节点菜单</el-button>
            </div>
            <div class="nodes-create">
              <NodeDraftForm
                ref="nodeFormRef"
                layout="full"
                @saved="handleNodeSaved"
              />
            </div>
          </template>

          <template v-else>
            <div class="nodes-toolbar">
              <el-button type="text" @click="enterNodesMenu">返回节点菜单</el-button>
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
        </section>

        <section v-else-if="activeNav === 'prompts'" class="workspace-pane workspace-pane--two-column">
          <PromptList
            class="workspace-pane__sidebar"
            @refresh="refreshPrompts"
            @delete="handleDeletePrompt"
          />
          <div class="workspace-pane__content">
            <PromptEditor ref="promptEditorRef" />
          </div>
        </section>

        <section v-else-if="activeNav === 'workflow'" class="workspace-pane">
          <WorkflowCanvas />
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
import { computed, ref, nextTick, onMounted, onBeforeUnmount, watch } from "vue";

import NodeDraftForm from "../components/NodeDraftForm.vue";
import NodeList from "../components/NodeList.vue";
import PromptEditor from "../components/PromptEditor.vue";
import PromptList from "../components/PromptList.vue";
import WorkflowCanvas from "../components/WorkflowCanvas.vue";
import VariablesPanel from "../components/VariablesPanel.vue";
import LogsPanel from "../components/LogsPanel.vue";
import NodeSubMenu from "../components/NodeSubMenu.vue";
import { usePipelineDraftStore } from "../stores/pipelineDraft";
import { usePromptDraftStore } from "../stores/promptDraft";
import { deletePipelineNode } from "../services/pipelineService";
import { deletePrompt } from "../services/promptService";

const pipelineStore = usePipelineDraftStore();
const promptStore = usePromptDraftStore();

const nodeFormRef = ref(null);
const promptEditorRef = ref(null);
const workspaceAside = ref(null);
const nodesMenuRef = ref(null);
const nodesMenuPopover = ref(null);

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
    title: "工作流画布",
    description: "使用 VueFlow 预览节点连线与执行顺序。",
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
const nodesViewMode = ref("manage");
const nodesMenuVisible = ref(false);
const nodesMenuPosition = ref(0);

const currentNav = computed(
  () => navItems.find((item) => item.id === activeNav.value) ?? navItems[0]
);

const otherNavItems = computed(() =>
  navItems.filter((item) => item.id !== "nodes")
);

const refreshNodes = () => nodeFormRef.value?.refresh?.();

const refreshPrompts = () => {
  promptEditorRef.value?.refresh?.();
};

const handlePrimaryAction = () => {
  if (activeNav.value === "prompts") {
    promptStore.resetSelection();
    promptEditorRef.value?.newEntry?.();
  }
};

const updateNodesMenuPosition = () => {
  const asideEl = workspaceAside.value?.$el ?? workspaceAside.value;
  const menuEl = nodesMenuRef.value?.$el ?? nodesMenuRef.value;
  if (!asideEl || !menuEl) return;
  const asideRect = asideEl.getBoundingClientRect();
  const menuRect = menuEl.getBoundingClientRect();
  nodesMenuPosition.value = menuRect.top - asideRect.top + menuRect.height / 2;
};

const showNodesMenu = () => {
  nodesMenuVisible.value = true;
  nextTick(updateNodesMenuPosition);
};

const handleMenuClick = (id) => {
  if (id === "nodes") {
    if (activeNav.value !== "nodes") {
      activeNav.value = "nodes";
    }
    if (nodesMenuVisible.value) {
      nodesMenuVisible.value = false;
    } else {
      showNodesMenu();
    }
  } else {
    activeNav.value = id;
    nodesMenuVisible.value = false;
  }
};

const enterNodesMenu = () => {
  if (activeNav.value !== "nodes") {
    activeNav.value = "nodes";
  }
  showNodesMenu();
};

const startCreateNode = async () => {
  nodesViewMode.value = "create";
  nodesTab.value = "form";
  pipelineStore.resetSelection();
  await nextTick();
  nodeFormRef.value?.newEntry?.();
};

const startManageNodes = async ({ nodeId } = {}) => {
  nodesViewMode.value = "manage";
  nodesTab.value = "form";
  await nextTick();
  await refreshNodes();
  if (nodeId) {
    pipelineStore.setSelectedNode(nodeId);
  }
};

const openCreateFromMenu = () => {
  nodesMenuVisible.value = false;
  startCreateNode();
};

const openManageFromMenu = () => {
  nodesMenuVisible.value = false;
  startManageNodes();
};

const handleNodeSaved = async ({ nodeId } = {}) => {
  await startManageNodes({ nodeId });
};

const handleDocumentClick = (event) => {
  if (!nodesMenuVisible.value) return;
  const menuEl = nodesMenuPopover.value;
  const nodeEl = nodesMenuRef.value?.$el ?? nodesMenuRef.value;
  if (menuEl?.contains(event.target) || nodeEl?.contains(event.target)) {
    return;
  }
  nodesMenuVisible.value = false;
};

onMounted(() => {
  document.addEventListener("click", handleDocumentClick);
  window.addEventListener("resize", updateNodesMenuPosition);
});

onBeforeUnmount(() => {
  document.removeEventListener("click", handleDocumentClick);
  window.removeEventListener("resize", updateNodesMenuPosition);
});

watch(activeNav, (val) => {
  if (val !== "nodes") {
    nodesMenuVisible.value = false;
  }
});

watch(nodesMenuVisible, (visible) => {
  if (visible) {
    nextTick(updateNodesMenuPosition);
  }
});

const handleDeleteNode = async (node) => {
  if (!node?.id) return;
  if (typeof window !== "undefined" && !window.confirm("确认删除该节点？")) {
    return;
  }
  try {
    await deletePipelineNode(node.id);
    pipelineStore.removeNodeDraft(node.id);
    if (pipelineStore.selectedNodeId === node.id) {
      pipelineStore.resetSelection();
      nodeFormRef.value?.newEntry?.();
    }
    refreshNodes();
  } catch (error) {
    console.error("删除节点失败", error);
  }
};

const handleDeletePrompt = async (prompt) => {
  if (!prompt?.id) return;
  if (typeof window !== "undefined" && !window.confirm("确认删除提示词？")) {
    return;
  }
  try {
    await deletePrompt(prompt.id);
    promptStore.removePromptDraft(prompt.id);
    if (promptStore.selectedPromptId === prompt.id) {
      promptStore.resetSelection();
      promptEditorRef.value?.newEntry?.();
    }
    refreshPrompts();
  } catch (error) {
    console.error("删除提示词失败", error);
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

.nodes-submenu-pop {
  position: absolute;
  left: calc(100% + var(--space-3));
  transform: translateY(-50%);
  z-index: 10;
}

.nodes-pane {
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

.nodes-manage {
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
