<template>
  <el-card class="node-submenu">
    <header class="node-submenu__header">
      <h3>节点操作</h3>
      <p>选择所需操作，进入不同的节点视图。</p>
    </header>
    <div class="node-submenu__actions">
      <el-button type="primary" @click="$emit('create')">
        新建节点
      </el-button>
      <el-button @click="$emit('manage')">
        查看已创建节点
      </el-button>
    </div>
  </el-card>
</template>

<script setup>
defineEmits(["create", "manage"]);
</script>

<style scoped>
.node-submenu {
  max-width: 520px;
  margin: 0 auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  box-shadow: var(--shadow-panel);
}

.node-submenu__header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
}

.node-submenu__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.node-submenu__actions {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.node-submenu__actions .el-button {
  min-width: 140px;
}
</style>
