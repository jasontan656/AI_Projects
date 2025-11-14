<template>
  <el-container class="workspace-shell">
    <el-aside width="248px" class="workspace-aside">
      <div class="workspace-brand">
        <h1>Up Ops Workspace</h1>
        <p>Workflow configuration for LLM pipelines</p>
      </div>
      <el-menu
        class="workspace-menu"
        :default-active="activeTab"
        :router="false"
      >
        <el-menu-item
          v-if="primaryNav"
          :index="primaryNav.id"
          data-testid="workspace-menu-item"
          :data-index="primaryNav.id"
          :disabled="primaryNav.id === 'workflow' && workflowBlocked"
          :title="primaryNav.id === 'workflow' && workflowBlocked ? workflowBlockedReason : ''"
          @click="handleMenuClick(primaryNav.id)"
        >
          <span>{{ primaryNav.label }}</span>
        </el-menu-item>
        <el-menu-item
          v-for="item in secondaryNavs"
          :key="item.id"
          :index="item.id"
          data-testid="workspace-menu-item"
          :data-index="item.id"
          :disabled="item.soon || (item.id === 'workflow' && workflowBlocked)"
          :title="item.id === 'workflow' && workflowBlocked ? workflowBlockedReason : ''"
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
          </div>
          <p class="workspace-desc">{{ currentNav.description }}</p>
        </div>
        <div class="workspace-actions">
          <slot name="actions" :tab="currentNav" />
        </div>
      </el-header>
      <el-main class="workspace-main">
        <RouterView v-slot="{ Component }">
          <transition name="fade">
            <KeepAlive
              include="NodesView,PromptsView,WorkflowView,VariablesView,LogsView,SettingsView"
            >
              <component
                v-if="Component"
                :is="Component"
                :key="route.fullPath || route.name"
                ref="activeViewRef"
                class="workspace-view-host"
              />
            </KeepAlive>
          </transition>
        </RouterView>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, provide, ref, watch, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { RouterView, useRoute, useRouter } from "vue-router";

import {
  useWorkspaceNavStore,
  WORKSPACE_TAB_ROUTE_MAP,
} from "../stores/workspaceNav";
import { usePipelineDraftStore } from "../stores/pipelineDraft";
import { usePromptDraftStore } from "../stores/promptDraft";
import { workspaceNavigationSymbol } from "../composables/useWorkspaceNavigation";

const router = useRouter();
const route = useRoute();
const navStore = useWorkspaceNavStore();
const pipelineStore = usePipelineDraftStore();
const promptStore = usePromptDraftStore();

const activeViewRef = ref(null);

const navItems = computed(() => navStore.navItems);
const primaryNav = computed(() => navItems.value[0]);
const secondaryNavs = computed(() => navItems.value.slice(1));
const currentNav = computed(() => navStore.currentNav);
const activeTab = computed(() => navStore.activeTab);
const workflowBlockedReason = computed(() => navStore.workflowBlockedReason);
const workflowBlocked = computed(() => Boolean(navStore.workflowBlockedReason));

const buildWorkflowRequirementMessage = () => {
  if (!pipelineStore.nodeCount && !promptStore.promptCount) {
    return "请先创建节点和提示词，再回到 Workflow";
  }
  if (!pipelineStore.nodeCount) {
    return "Workflow 需要至少 1 个节点";
  }
  return "Workflow 需要至少 1 个提示词";
};

const updateWorkflowBlockedState = () => {
  if (pipelineStore.nodeCount > 0 && promptStore.promptCount > 0) {
    navStore.setWorkflowBlocked("");
    return;
  }
  navStore.setWorkflowBlocked(buildWorkflowRequirementMessage());
};

const hydratePrerequisites = async () => {
  const tasks = [];
  if (!pipelineStore.nodeCount) {
    tasks.push(
      pipelineStore
        .refreshNodes({ pageSize: 50 })
        .catch((error) => console.warn("[workspace] 加载节点失败", error))
    );
  }
  if (!promptStore.promptCount) {
    tasks.push(
      promptStore
        .refreshPrompts({ pageSize: 50 })
        .catch((error) => console.warn("[workspace] 加载提示词失败", error))
    );
  }
  if (tasks.length) {
    await Promise.all(tasks);
  }
};

const ensureWorkflowReady = async ({ silent = false } = {}) => {
  await hydratePrerequisites();
  const ready = pipelineStore.nodeCount > 0 && promptStore.promptCount > 0;
  updateWorkflowBlockedState();
  if (!ready && !silent) {
    ElMessage.warning(buildWorkflowRequirementMessage());
  }
  if (
    !ready &&
    route.name === WORKSPACE_TAB_ROUTE_MAP.workflow
  ) {
    const fallback =
      pipelineStore.nodeCount > 0
        ? WORKSPACE_TAB_ROUTE_MAP.prompts
        : WORKSPACE_TAB_ROUTE_MAP.nodes;
    router.replace({ name: fallback }).catch(() => {});
  }
  return ready;
};

const routeToTabMap = Object.entries(WORKSPACE_TAB_ROUTE_MAP).reduce(
  (acc, [tab, name]) => {
    acc[name] = tab;
    return acc;
  },
  {}
);

const deriveTabFromRoute = (currentRoute) => {
  if (!currentRoute) {
    return null;
  }
  if (currentRoute.name && routeToTabMap[currentRoute.name]) {
    return routeToTabMap[currentRoute.name];
  }
  const path = currentRoute.path ?? currentRoute.fullPath ?? "";
  const match = /\/workspace\/([^/]+)/.exec(path);
  if (match && WORKSPACE_TAB_ROUTE_MAP[match[1]]) {
    return match[1];
  }
  return null;
};

watch(
  () => route.name,
  () => {
    const tabId = deriveTabFromRoute(route);
    if (tabId) {
      navStore.setActiveTab(tabId);
    }
  },
  { immediate: true }
);

watch(
  () => [pipelineStore.nodeCount, promptStore.promptCount],
  () => {
    updateWorkflowBlockedState();
  }
);

onMounted(() => {
  void ensureWorkflowReady({ silent: true });
});

const navigateToTab = async (targetId, meta = {}) => {
  if (!WORKSPACE_TAB_ROUTE_MAP[targetId]) {
    return;
  }
  if (targetId === "workflow") {
    const ready = await ensureWorkflowReady();
    if (!ready) {
      return;
    }
  }
  const currentId = navStore.activeTab;
  if (targetId === currentId) {
    await activeViewRef.value?.resetView?.(meta);
    return;
  }
  const canLeave = await navStore.ensureCanLeave(currentId);
  if (!canLeave) {
    return;
  }
  navStore.recordNavigation(targetId, { reason: meta.reason ?? "menu" });
  await router.push({ name: WORKSPACE_TAB_ROUTE_MAP[targetId] });
};

const handleMenuClick = async (tabId) => {
  await navigateToTab(tabId, { reason: "menu" });
};

provide(workspaceNavigationSymbol, {
  navigate: (tabId, meta = {}) =>
    navigateToTab(tabId, { ...meta, reason: meta.reason ?? "programmatic" }),
  markLogsConnection: (status) => navStore.markLogsConnection(status),
});
</script>

<style scoped>
.workspace-shell {
  min-height: 100vh;
  background: var(--color-bg-app, #f5f6fb);
}

.workspace-aside {
  background: white;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  border-right: 1px solid var(--color-border-subtle);
}

.workspace-brand h1 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.workspace-brand p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
}

.workspace-menu {
  border-right: none;
}

.workspace-menu__soon {
  margin-left: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.workspace-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
  gap: var(--space-3);
}

.workspace-title-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.workspace-title {
  margin: 0;
  font-size: var(--font-size-xl);
}

.workspace-section {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  text-transform: uppercase;
}

.workspace-desc {
  margin: var(--space-1) 0 0;
  color: var(--color-text-secondary);
  max-width: 640px;
}

.workspace-main {
  padding: var(--space-4);
  background: var(--color-bg-muted, #f3f4f9);
}

.workspace-view-host {
  width: 100%;
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
  }
}
</style>

<style>
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

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
