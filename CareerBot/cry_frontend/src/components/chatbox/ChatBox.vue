<template>
  <div class="ChatBox-container" :style="chatboxStyles">
    <div class="ChatBox-wrapper">
      <AddButton @click="addNewChat" />
      <input
        type="text"
        class="ChatBox-input"
        placeholder="Ask anything"
        v-model="inputText"
        @keyup.enter="sendMessage"
      />
      <SendMessageButton @click="sendMessage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import SendMessageButton from './SendMessageButton.vue'
import AddButton from './AddButton.vue'

const props = defineProps<{
  modelValue?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'send', value: string): void
  (e: 'add'): void
}>()

const DEFAULT_CHATBOX_Z_INDEX = 100

const inputText = ref(props.modelValue || '')

watch(
  () => props.modelValue,
  (value) => {
    if (typeof value === 'string' && value !== inputText.value) {
      inputText.value = value
    }
  }
)

const chatboxStyles = computed(() => ({
  zIndex: DEFAULT_CHATBOX_Z_INDEX
}))

const sendMessage = () => {
  const trimmed = inputText.value.trim()
  if (!trimmed) {
    return
  }

  emit('send', trimmed)
  emit('update:modelValue', '')
  inputText.value = ''
}

const addNewChat = () => {
  emit('add')
}
</script>

<style scoped>
.ChatBox-container {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background: white;
  padding: 12px;
}

.ChatBox-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 480px;
  margin: 0 auto;
  border: 1px solid rgb(233, 226, 226);
  background: white;
  border-radius: 24px;
  padding: 8px 12px;
}

.ChatBox-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  padding: 8px;
  font-size: 16px;
}

.ChatBox-input::placeholder {
  opacity: 0.5;
}

@media (max-width: 480px) {
  .ChatBox-wrapper {
    max-width: 100%;
    margin: 0 12px;
  }
}
</style>
