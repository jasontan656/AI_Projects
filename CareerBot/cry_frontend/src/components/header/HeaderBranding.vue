<template>
  <div class="brand-logo">
    <div class="brand-title">{{ title }}</div>
    <div class="brand-powered">{{ tagline }}</div>
  </div>
</template>

<script setup lang="ts">
import { toRefs, withDefaults, defineProps } from 'vue'

const props = withDefaults(defineProps<{
  title?: string
  tagline?: string
}>(), {
  title: 'Career Bot',
  tagline: 'Powered by 4ways group'
})

const { title, tagline } = toRefs(props)
</script>

<style scoped>
.brand-logo {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-end;
  flex: 1;
  height: 100%;
  gap: 2px;
  padding: 0 16px;
  line-height: 1.1;
  transform: translateY(-4px);
}

.brand-title {
  font-size: 20px;
  font-weight: 700;
  color: #333;
  text-align: right;
  line-height: 1.1;
}

.brand-powered {
  font-size: 10px;
  color: #666;
  text-align: right;
  white-space: nowrap;
  line-height: 1.1;
}

@media (min-width: 480px) {
  .brand-title {
    font-size: 22px;
  }

  .brand-powered {
    font-size: 11px;
  }
}
</style>
