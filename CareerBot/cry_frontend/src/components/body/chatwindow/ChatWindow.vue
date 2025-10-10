<template>
  <div class="chat-window">
    <div class="chat-window__placeholder">
      <slot>Waiting for messages...</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
// Static chat window shell for future integration
</script>

<style scoped>
.chat-window {
  display: flex;
  flex: 1;
  min-height: 0;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.chat-window__placeholder {
  margin: auto;
  color: rgba(0, 0, 0, 0.4);
  font-size: 14px;
}
</style>
