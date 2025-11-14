<template>
  <section class="channel-form" v-if="published">
    <header class="channel-form__header">
      <div>
        <h3>{{ title }}</h3>
        <p>{{ subtitle }}</p>
      </div>
      <div class="channel-form__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="channel-form__body">
      <slot name="coverage" />
      <slot />
    </div>
  </section>
  <section v-else class="channel-form__placeholder">
    <el-empty :description="emptyDescription">
      <el-button type="primary" @click="$emit('go-publish')">
        前往发布
      </el-button>
    </el-empty>
  </section>
</template>

<script setup>
defineProps({
  published: {
    type: Boolean,
    default: false,
  },
  title: {
    type: String,
    default: "渠道配置",
  },
  subtitle: {
    type: String,
    default: "请完善渠道所需的密钥、Webhook 等信息。",
  },
  emptyDescription: {
    type: String,
    default: "请先发布 Workflow 才能绑定渠道",
  },
});

defineEmits(["go-publish"]);
</script>

<style scoped>
.channel-form {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.channel-form__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

.channel-form__header h3 {
  margin: 0;
}

.channel-form__header p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.channel-form__actions {
  display: flex;
  gap: var(--space-2);
}

.channel-form__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.channel-form__placeholder {
  border: 1px dashed var(--color-border-default);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  text-align: center;
  background: var(--color-bg-subtle);
}
</style>
