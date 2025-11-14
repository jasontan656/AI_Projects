<template>
  <section class="channel-rate-limit-form">
    <div class="channel-rate-limit-form__field">
      <label>允许的 chatId</label>
      <el-select
        v-model="metadata.allowedChatIds"
        multiple
        filterable
        allow-create
        default-first-option
        placeholder="输入 chatId 回车添加"
        data-test="rate-limit-chat-ids"
      />
      <p class="channel-rate-limit-form__hint">
        留空表示不限；建议填生产群/用户 chatId。
      </p>
    </div>
    <div class="channel-rate-limit-form__field">
      <label>速率限制（次/分钟）</label>
      <el-input-number
        v-model="metadata.rateLimitPerMin"
        :min="1"
        :max="600"
        :step="1"
        :controls="false"
        data-test="rate-limit-input"
      />
      <p v-if="errors.rateLimitPerMin" class="channel-rate-limit-form__error">
        {{ errors.rateLimitPerMin }}
      </p>
    </div>
    <div class="channel-rate-limit-form__field">
      <label>Locale</label>
      <el-select v-model="metadata.locale">
        <el-option label="中文" value="zh-CN" />
        <el-option label="English" value="en-US" />
      </el-select>
    </div>
  </section>
</template>

<script setup>
defineProps({
  metadata: {
    type: Object,
    required: true,
  },
  errors: {
    type: Object,
    required: true,
  },
});
</script>

<style scoped>
.channel-rate-limit-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}

.channel-rate-limit-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.channel-rate-limit-form__hint {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.channel-rate-limit-form__error {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--color-danger);
}
</style>
