<template>
  <div class="message-bubble" :class="{ 'message-bubble--user': isUser, 'message-bubble--ai': !isUser }">
    <div class="message-bubble__content">
      <p class="message-text">{{ displayContent }}</p>
      <p v-if="formattedTime" class="message-time">{{ formattedTime }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, withDefaults } from 'vue'

const props = withDefaults(defineProps<{
  content?: string
  isUser?: boolean
  timestamp?: Date
}>(), {
  content: '',
  isUser: false,
  timestamp: undefined
})

const displayContent = computed(() => props.content || '')

const formattedTime = computed(() => {
  if (!props.timestamp) {
    return ''
  }

  return props.timestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  })
})
</script>

<style scoped>
.message-bubble {
  display: flex;
  width: 100%;
  margin: 8px 0;
}

.message-bubble--user {
  justify-content: flex-end;
}

.message-bubble--ai {
  justify-content: flex-start;
}

.message-bubble__content {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 16px;
  background: #f2f2f2;
  color: #1a1a1a;
  line-height: 1.4;
}

.message-bubble--user .message-bubble__content {
  background: #0056ff;
  color: #ffffff;
}

.message-text {
  margin: 0;
  font-size: 14px;
}

.message-time {
  margin: 8px 0 0;
  font-size: 12px;
  opacity: 0.6;
}

@media (prefers-color-scheme: dark) {
  .message-bubble__content {
    background: #1f1f1f;
    color: #f0f0f0;
  }

  .message-bubble--user .message-bubble__content {
    background: #3a71ff;
  }
}
</style>
