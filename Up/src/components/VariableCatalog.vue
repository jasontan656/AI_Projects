<template>
  <section class="catalog">
    <header>
      <div>
        <h3>变量目录</h3>
        <p>Workflow 中可用的上下文变量，可直接复制键名。</p>
      </div>
      <el-button link size="small" @click="$emit('refresh')">刷新</el-button>
    </header>
    <el-input
      v-model="keyword"
      placeholder="搜索变量"
      size="small"
      clearable
      class="catalog__search"
    />
    <el-empty v-if="!filtered.length" description="暂无变量" />
    <el-table v-else :data="filtered" border size="small">
      <el-table-column prop="key" label="变量" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="scope" label="作用域" width="120" />
      <el-table-column width="100">
        <template #default="{ row }">
          <el-button text size="small" @click="copy(row.key)">复制</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";

const props = defineProps({
  variables: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["refresh"]);

const keyword = ref("");

const filtered = computed(() => {
  if (!keyword.value) return props.variables;
  const text = keyword.value.toLowerCase();
  return props.variables.filter(
    (item) =>
      item.key?.toLowerCase().includes(text) ||
      (item.description || "").toLowerCase().includes(text)
  );
});

const copy = async (value) => {
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    ElMessage.success("已复制变量");
  } catch {
    ElMessage.error("复制失败");
  }
};
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

.catalog__search {
  width: 100%;
}
</style>
