<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

const applyDocumentLayout = () => {
  document.documentElement.style.height = '100%'
  document.body.style.margin = '0'
  document.body.style.height = '100%'
  document.body.style.overflow = 'hidden'
}

const restoreDocumentLayout = (snapshot: Record<string, string>) => {
  document.documentElement.style.height = snapshot.htmlHeight
  document.body.style.margin = snapshot.bodyMargin
  document.body.style.height = snapshot.bodyHeight
  document.body.style.overflow = snapshot.bodyOverflow
}

const snapshot = {
  htmlHeight: '',
  bodyMargin: '',
  bodyHeight: '',
  bodyOverflow: ''
}

onMounted(() => {
  snapshot.htmlHeight = document.documentElement.style.height
  snapshot.bodyMargin = document.body.style.margin
  snapshot.bodyHeight = document.body.style.height
  snapshot.bodyOverflow = document.body.style.overflow

  applyDocumentLayout()
})

onBeforeUnmount(() => {
  restoreDocumentLayout(snapshot)
})
</script>

<template>
  <div id="app" class="app-root">
    <RouterView />
  </div>
</template>

<style scoped>
.app-root {
  width: 100vw;
  height: 100vh;
  max-width: 100vw;
  max-height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
