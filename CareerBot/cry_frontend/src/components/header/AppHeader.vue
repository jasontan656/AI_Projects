<template>
  <header class="app-header" :style="headerStyle">
    <div class="app-header__wrapper">
      <div class="app-header__left">
        <HeaderBurgerMenu :active="menuOpen" @toggle="handleMenuToggle" />
      </div>
      <HeaderBranding class="app-header__branding" :title="title" :tagline="tagline" />
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, ref, toRefs, withDefaults, defineProps, defineEmits } from 'vue'
import HeaderBurgerMenu from './HeaderBurgerMenu.vue'
import HeaderBranding from './HeaderBranding.vue'

const props = withDefaults(defineProps<{
  title?: string
  tagline?: string
}>(), {
  title: 'Career Bot',
  tagline: 'Powered by 4ways group'
})

const { title, tagline } = toRefs(props)

const emit = defineEmits<{
  (e: 'toggle-menu', value: boolean): void
}>()

const menuOpen = ref(false)
const DEFAULT_HEADER_Z_INDEX = 100

const headerStyle = computed(() => ({
  zIndex: DEFAULT_HEADER_Z_INDEX
}))

const handleMenuToggle = () => {
  menuOpen.value = !menuOpen.value
  emit('toggle-menu', menuOpen.value)
}
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  left: 0;
  right: 0;
  width: 100%;
  min-height: 48px;
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
}

.app-header__wrapper {
  display: flex;
  align-items: center;
  width: 100%;
  height: 100%;
  background: #ffffff;
}

.app-header__left {
  display: flex;
  align-items: center;
}

.app-header__branding {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}
</style>
