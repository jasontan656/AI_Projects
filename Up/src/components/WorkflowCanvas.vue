<template>
  <section class="workflow-canvas">
    <header class="workflow-canvas__header">
      <h2>Workflow 画布</h2>
      <p>根据节点顺序展示执行关系，提示词绑定将显示在节点标签中。</p>
    </header>
    <div class="workflow-canvas__body">
      <VueFlow
        fit-view
        :nodes="computedNodes"
        :edges="computedEdges"
        class="workflow-canvas__flow"
        :default-viewport="{ zoom: 0.9, x: 0, y: 0 }"
      />
    </div>
    <footer class="workflow-canvas__footer">
      <p v-if="!nodeSequence.length">暂无节点，请先在编辑器中配置节点顺序。</p>
      <p v-else>后续可在此支持拖拽与高级编辑，目前仅提供只读预览。</p>
    </footer>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { VueFlow } from "@vue-flow/core";
import "@vue-flow/core/dist/style.css";

const props = defineProps({
  nodeSequence: {
    type: Array,
    default: () => [],
  },
  nodes: {
    type: Array,
    default: () => [],
  },
  promptBindings: {
    type: Array,
    default: () => [],
  },
});

const nodeMap = computed(() => {
  const map = new Map();
  (props.nodes || []).forEach((node) => {
    if (node?.id) {
      map.set(node.id, node);
    }
  });
  return map;
});

const promptMap = computed(() => {
  const map = new Map();
  (props.promptBindings || []).forEach((binding) => {
    if (binding?.nodeId) {
      map.set(binding.nodeId, binding.promptId || null);
    }
  });
  return map;
});

const computedNodes = computed(() => {
  const spacingX = 220;
  const spacingY = 120;
  return props.nodeSequence.map((nodeId, index) => {
    const node = nodeMap.value.get(nodeId) || {};
    const promptId = promptMap.value.get(nodeId);
    return {
      id: nodeId,
      type: index === 0 ? "input" : index === props.nodeSequence.length - 1 ? "output" : "default",
      label: node.name || nodeId,
      position: { x: spacingX * index, y: spacingY * (index % 2) },
      data: {
        description: promptId ? `绑定提示词：${promptId}` : "使用节点默认提示词",
      },
    };
  });
});

const computedEdges = computed(() => {
  const edges = [];
  for (let i = 0; i < props.nodeSequence.length - 1; i += 1) {
    edges.push({
      id: `${props.nodeSequence[i]}-${props.nodeSequence[i + 1]}`,
      source: props.nodeSequence[i],
      target: props.nodeSequence[i + 1],
      animated: true,
    });
  }
  return edges;
});
</script>

<style scoped>
.workflow-canvas {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
  background: var(--color-bg-panel);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel);
  min-height: 420px;
}

.workflow-canvas__header h2 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.workflow-canvas__header p,
.workflow-canvas__footer p {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.workflow-canvas__body {
  flex: 1;
  min-height: 320px;
  border: 1px dashed var(--color-border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-bg-muted);
}

.workflow-canvas__flow {
  width: 100%;
  height: 100%;
}
</style>
