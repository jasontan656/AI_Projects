<template>
  <div class="home-content">
    <div class="chat-container">
      <ChatWindow />
    </div>
  </div>
</template>

<script setup lang="ts">
import ChatWindow from './chatwindow/ChatWindow.vue'
</script>

<style scoped>
.home-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0;
  background: #f8f9fa;
  overflow: hidden;
  min-height: 0;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  min-height: 0;
}

.chat-container > * {
  flex: 1;
  min-height: 0;
}

@media (max-width: 480px) {
  .home-content {
    padding: 0;
    background: #fff;
  }

  .chat-container {
    flex: 1;
    margin: 0;
    border-radius: 0;
    box-shadow: none;
    min-height: 100%;
  }
}

@media (prefers-color-scheme: dark) {
  .home-content {
    background: #121212;
  }

  .chat-container {
    background: #1a1a1a;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  @media (max-width: 480px) {
    .home-content {
      background: #1a1a1a;
    }

    .chat-container {
      background: #1a1a1a;
    }
  }
}

@media (min-width: 768px) {
  .chat-container {
    margin: 24px;
    border-radius: 16px;
  }
}
</style>
