<template>
  <section class="workflow-canvas">
    <header class="workflow-canvas__header">
      <h2>Workflow Preview</h2>
      <p>使用 VueFlow 预览节点与连线，后端对接完成后可替换为真实数据。</p>
    </header>
    <div class="workflow-canvas__body">
      <VueFlow
        fit-view
        :nodes="nodes"
        :edges="edges"
        class="workflow-canvas__flow"
        :default-viewport="{ zoom: 0.9, x: 0, y: 0 }"
      />
    </div>
    <footer class="workflow-canvas__footer">
      <p>
        当前展示为静态示例。后续实现中将从 pipeline store 生成节点、边并支持拖拽与节点设置。
      </p>
    </footer>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { VueFlow } from "@vue-flow/core";

const nodes = computed(() => [
  {
    id: "start",
    type: "input",
    label: "入口节点",
    position: { x: 0, y: 80 },
    data: { description: "初始化上下文" },
  },
  {
    id: "llm",
    type: "default",
    label: "LLM 动作",
    position: { x: 220, y: 40 },
    data: { description: "prompt_append" },
  },
  {
    id: "tool",
    type: "default",
    label: "工具调用",
    position: { x: 220, y: 180 },
  },
  {
    id: "end",
    type: "output",
    label: "输出节点",
    position: { x: 440, y: 110 },
  },
]);

const edges = computed(() => [
  { id: "start-llm", source: "start", target: "llm" },
  { id: "start-tool", source: "start", target: "tool" },
  { id: "llm-end", source: "llm", target: "end", animated: true },
  { id: "tool-end", source: "tool", target: "end" },
]);
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
