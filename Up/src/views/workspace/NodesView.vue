<template>
  <section class="workspace-pane nodes-pane">
    <template v-if="nodesStage === 'menu'">
      <NodeSubMenu :actions="nodeActions" @select="handleNodeActionSelect" />
    </template>

    <template v-else-if="nodesStage === 'create'">
      <div class="nodes-toolbar">
        <el-button text @click="enterNodesMenu">返回节点菜单</el-button>
      </div>
      <div class="nodes-create">
        <NodeDraftForm ref="nodeFormRef" layout="full" @saved="handleNodeSaved" />
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
            <el-tab-pane label="节点配置" name="form">
              <NodeDraftForm ref="nodeFormRef" layout="split" @saved="handleNodeSaved" />
            </el-tab-pane>
            <el-tab-pane label="脚本预览（即将推出）" name="preview">
              <el-empty
                class="workspace-placeholder"
                description="后续将在此提供节点动作 JSON 预览与导出功能"
              />
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </template>

    <template v-else>
      <el-empty description="当前阶段暂无内容" />
    </template>
  </section>
</template>

<script setup>
defineOptions({ name: "NodesView" });

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import NodeDraftForm from "../../components/NodeDraftForm.vue";
import NodeList from "../../components/NodeList.vue";
import NodeSubMenu from "../../components/NodeSubMenu.vue";
import { usePipelineDraftStore } from "../../stores/pipelineDraft";
import { deletePipelineNode, listPipelineNodes } from "../../services/pipelineService";
import { useWorkspaceNavStore } from "../../stores/workspaceNav";

const pipelineStore = usePipelineDraftStore();
const navStore = useWorkspaceNavStore();

const nodeFormRef = ref(null);
const nodesStage = ref("menu");
const nodesTab = ref("form");

const nodeActions = computed(() => [
  {
    id: "create",
    label: "新建节点",
    description: "从空白模版开始构建节点配置与动作脚本。",
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
      pipelineStore.nodeCount === 0 ? "暂无节点，请先创建一个节点再进入管理。" : "",
  },
]);

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

const ensureCanLeaveStage = async () => {
  if (nodesStage.value !== "create") {
    return true;
  }
  const dirty = nodeFormRef.value?.isDirty?.();
  if (!dirty) {
    return true;
  }
  try {
    await ElMessageBox.confirm(
      "当前节点草稿尚未保存，确定要离开吗？",
      "未保存的更改",
      {
        confirmButtonText: "仍然离开",
        cancelButtonText: "返回编辑",
        type: "warning",
      }
    );
    return true;
  } catch {
    return false;
  }
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

const handleNodeSaved = async ({ nodeId } = {}) => {
  await startManageNodes({ nodeId });
};

const handleDeleteNode = async (node) => {
  if (!node?.id) return;
  try {
    await ElMessageBox.confirm(
      "确认删除该节点？该操作无法撤销。",
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

watch(
  () => navStore.activeTab,
  async (tab) => {
    if (tab === "nodes") {
      await setNodesStage("menu", { force: true, skipLeaveGuard: true });
    }
  }
);

const unregisterGuard = navStore.registerGuard("nodes", ensureCanLeaveStage);

onMounted(() => {
  primeNodes();
});

onUnmounted(() => {
  unregisterGuard();
});

defineExpose({
  resetView: () => setNodesStage("menu", { force: true, skipLeaveGuard: true }),
});
</script>

<style scoped>
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
</style>
