<template>
  <button
    type="button"
    class="burger-menu"
    :class="{ 'burger-menu--active': isActive }"
    @click="handleClick"
    aria-label="Toggle navigation"
  >
    <span class="burger-menu__line"></span>
    <span class="burger-menu__line burger-menu__line--medium"></span>
    <span class="burger-menu__line burger-menu__line--short"></span>
  </button>
</template>

<script setup lang="ts">
import { computed, withDefaults, defineProps, defineEmits } from 'vue'

const props = withDefaults(defineProps<{
  active?: boolean
}>(), {
  active: false
})

const emit = defineEmits<{
  (e: 'toggle'): void
}>()

const isActive = computed(() => props.active)

const handleClick = () => {
  emit('toggle')
}
</script>

<style scoped>
.burger-menu {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 6px;
  width: 50px;
  height: 50px;
  border: none;
  background: transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: background-color 0.3s ease, opacity 0.3s ease;
  padding: 0 0 0 12px;
}

.burger-menu:hover {
  background-color: rgba(0, 0, 0, 0.05);
  opacity: 0.9;
}

.burger-menu:focus-visible {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

.burger-menu__line {
  height: 2px;
  border-radius: 999px;
  background: #333;
  transition: transform 0.3s ease, width 0.3s ease, background-color 0.3s ease, opacity 0.3s ease;
  width: 26px;
  transform-origin: left center;
}

.burger-menu__line--medium {
  width: 20px;
}

.burger-menu__line--short {
  width: 14px;
}

.burger-menu:hover .burger-menu__line {
  background: #555;
}

.burger-menu--active .burger-menu__line:first-child {
  transform: translateY(4px) rotate(45deg);
  width: 24px;
}

.burger-menu--active .burger-menu__line:nth-child(2) {
  opacity: 0;
}

.burger-menu--active .burger-menu__line:last-child {
  transform: translateY(-4px) rotate(-45deg);
  width: 24px;
}
</style>
