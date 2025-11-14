<template>
  <section class="channel-security-panel">
    <header class="channel-security-panel__header">
      <div>
        <h4>安全校验</h4>
        <p>配置 Webhook Secret / TLS 证书，并在保存前执行唯一性校验。</p>
      </div>
      <el-button
        size="small"
        type="primary"
        plain
        :loading="validating"
        :disabled="disabled"
        @click="$emit('validate')"
        data-test="security-validate-button"
      >
        校验 Secret/TLS
      </el-button>
    </header>
    <ChannelFieldsSecurity
      :secret="security.secret"
      :certificate="security.certificatePem"
      :certificate-name="security.certificateName"
      :validation-result="validationResult"
      :validating="validating"
      :validation-error="validationError"
      :disabled="disabled"
      @update:secret="(value) => $emit('update:secret', value)"
      @update:certificate="(value) => $emit('update:certificate', value)"
      @update:certificate-name="(value) => $emit('update:certificate-name', value)"
    />
  </section>
</template>

<script setup>
import ChannelFieldsSecurity from "./ChannelFieldsSecurity.vue";

defineProps({
  security: {
    type: Object,
    required: true,
  },
  validationResult: {
    type: Object,
    default: () => null,
  },
  validating: {
    type: Boolean,
    default: false,
  },
  validationError: {
    type: String,
    default: "",
  },
  disabled: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["validate", "update:secret", "update:certificate", "update:certificate-name"]);
</script>

<style scoped>
.channel-security-panel {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.channel-security-panel__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  align-items: center;
}

.channel-security-panel__header h4 {
  margin: 0;
}

.channel-security-panel__header p {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
</style>
