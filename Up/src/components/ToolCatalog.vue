<template>
  <section class="catalog">
    <header>
      <div>
        <h3>工具目录</h3>
        <p>展示 workflow 可用的工具能力。</p>
      </div>
      <el-button link size="small" @click="$emit('refresh')">刷新</el-button>
    </header>
    <el-empty v-if="!tools.length" description="暂无工具" />
    <el-table v-else :data="tools" border size="small">
      <el-table-column prop="name" label="工具名称" />
      <el-table-column prop="type" label="类别" width="140" />
      <el-table-column prop="description" label="描述" />
    </el-table>
  </section>
</template>

<script setup>
defineProps({
  tools: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["refresh"]);
</script>

<style scoped>
.catalog {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-bg-panel);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  height: 100%;
}

.catalog header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
