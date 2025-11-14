<template>
  <section class="channel-credential-card">
    <el-form-item label="Bot Token" :error="errors.botToken">
      <template v-if="showTokenInput">
        <el-input
          v-model.trim="form.botToken"
          type="password"
          show-password
          placeholder="请输入 Bot Token"
          data-test="credential-token-input"
        />
        <el-button
          v-if="hasMaskedToken"
          text
          size="small"
          @click="$emit('cancel-token-edit')"
          data-test="credential-token-cancel"
        >
          保留原 Token
        </el-button>
      </template>
      <template v-else>
        <div class="channel-credential-card__token-mask">
          <span>{{ maskedToken }}</span>
          <el-button
            text
            size="small"
            @click="$emit('enable-token-edit')"
            data-test="credential-token-edit"
          >
            重新输入 Token
          </el-button>
        </div>
      </template>
    </el-form-item>

    <el-form-item label="Webhook URL" :error="errors.webhookUrl">
      <el-input
        v-model.trim="form.webhookUrl"
        placeholder="https://example.com/telegram"
        :disabled="pollingMode"
      />
      <p v-if="showWebhookWarning" class="channel-credential-card__warning">
        当前域名未在白名单中，保存后请确认入口代理允许该地址。
      </p>
      <p v-if="pollingMode" class="channel-credential-card__hint">
        Polling 模式会停用 Webhook 并改为人工触发更新。
      </p>
    </el-form-item>

    <el-form-item label="使用 Polling 模式">
      <div class="channel-credential-card__inline">
        <el-switch
          :model-value="pollingMode"
          @change="$emit('toggle-polling')"
          data-test="credential-polling-switch"
        />
        <span class="channel-credential-card__hint">
          启用后 webhook 将被禁用，覆盖测试仅提供记录，结果需手动验证。
        </span>
      </div>
    </el-form-item>

    <el-form-item label="等待节点结果">
      <el-switch v-model="form.waitForResult" />
    </el-form-item>

    <el-form-item
      label="Workflow 缺失提示（支持 {workflow_id}）"
      :error="errors.workflowMissingMessage"
    >
      <el-input
        v-model="form.workflowMissingMessage"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 3 }"
      />
    </el-form-item>

    <el-form-item
      label="超时提示（支持 {correlation_id}）"
      :error="errors.timeoutMessage"
    >
      <el-input
        v-model="form.timeoutMessage"
        type="textarea"
        :autosize="{ minRows: 2, maxRows: 3 }"
      />
    </el-form-item>
  </section>
</template>

<script setup>
defineProps({
  form: {
    type: Object,
    required: true,
  },
  errors: {
    type: Object,
    required: true,
  },
  showTokenInput: {
    type: Boolean,
    default: false,
  },
  hasMaskedToken: {
    type: Boolean,
    default: false,
  },
  maskedToken: {
    type: String,
    default: "",
  },
  pollingMode: {
    type: Boolean,
    default: false,
  },
  showWebhookWarning: {
    type: Boolean,
    default: false,
  },
});

defineEmits(["enable-token-edit", "cancel-token-edit", "toggle-polling"]);
</script>

<style scoped>
.channel-credential-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.channel-credential-card__token-mask {
  display: inline-flex;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
}

.channel-credential-card__hint {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.channel-credential-card__warning {
  margin: var(--space-1) 0 0;
  font-size: var(--font-size-xs);
  color: #a45c00;
}

.channel-credential-card__inline {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
</style>
