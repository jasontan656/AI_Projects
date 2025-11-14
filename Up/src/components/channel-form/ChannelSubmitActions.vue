<template>
  <div class="submit-actions">
    <el-button
      text
      :disabled="disabled || unbinding || !hasExistingBinding"
      :loading="unbinding"
      @click="$emit('unbind')"
    >
      解绑渠道
    </el-button>
    <el-tooltip
      v-if="saveDisabledReason"
      placement="top"
      :content="saveDisabledReason"
    >
      <el-button
        type="primary"
        :disabled="Boolean(saveDisabledReason) || disabled"
        :loading="saving"
        @click="$emit('save')"
      >
        保存配置
      </el-button>
    </el-tooltip>
    <el-button
      v-else
      type="primary"
      :disabled="disabled"
      :loading="saving"
      @click="$emit('save')"
    >
      保存配置
    </el-button>
  </div>
</template>

<script setup>
defineProps({
  saving: {
    type: Boolean,
    default: false,
  },
  unbinding: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  hasExistingBinding: {
    type: Boolean,
    default: false,
  },
  saveDisabledReason: {
    type: String,
    default: "",
  },
});

defineEmits(["save", "unbind"]);
</script>

<style scoped>
.submit-actions {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
</style>
