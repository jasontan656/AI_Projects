<template>
  <section class="security-fields">
    <header>
      <div>
        <h4>Secret & TLS</h4>
        <p>配置 Telegram Webhook Secret 与证书，确保唯一性与可用性。</p>
      </div>
      <el-button
        type="primary"
        size="small"
        :loading="validating"
        :disabled="!secretValue"
        data-test="security-validate-btn"
        @click="handleValidate"
      >
        校验 Secret/TLS
      </el-button>
    </header>

    <el-form label-position="top" class="security-fields__form">
      <el-form-item
        label="Webhook Secret"
        :error="secretError"
        data-test="security-secret-item"
      >
        <el-input
          v-model.trim="secretValue"
          placeholder="1-256 位，仅支持 字母/数字/_/-"
          maxlength="256"
          data-test="security-secret-input"
        />
        <p class="security-fields__hint">
          Secret 将写入 Telegram `X-Telegram-Bot-Api-Secret-Token`，禁止在多个 workflow 复用。
        </p>
      </el-form-item>

      <el-form-item label="上传 TLS 证书（PEM）" data-test="security-cert-item">
        <el-upload
          class="security-fields__upload"
          accept=".pem,.crt,.cer"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleCertChange"
        >
          <el-button type="default" size="small">选择证书</el-button>
        </el-upload>
        <p v-if="certificateName" class="security-fields__hint">
          已选择：{{ certificateName }}
        </p>
        <p v-else class="security-fields__hint">
          支持 PEM/CRT；若未上传，将使用现有证书。
        </p>
      </el-form-item>
    </el-form>

    <div v-if="validationError" class="security-fields__alert">
      <el-alert
        type="error"
        :closable="false"
        show-icon
        data-test="security-error"
        title="Secret/TLS 校验失败"
        :description="validationError"
      />
    </div>

    <div v-if="validationResult" class="security-fields__status">
      <el-alert
        v-if="!validationResult.secret?.isUnique"
        type="error"
        :closable="false"
        show-icon
        data-test="security-secret-conflict"
        title="Secret 已被以下 Workflow 使用"
        :description="conflictList"
      />
      <el-alert
        v-else
        type="success"
        :closable="false"
        show-icon
        data-test="security-secret-ok"
        title="Secret 唯一性通过"
      />

      <el-alert
        v-if="shouldWarnCertificate"
        type="warning"
        :closable="false"
        show-icon
        data-test="security-cert-warning"
      >
        <template #title>
          证书将在 {{ certificateDays }} 天内到期
        </template>
        <template #default>
          <p class="security-fields__warning">
            请在到期前更换证书并重新运行覆盖测试。
          </p>
        </template>
      </el-alert>

      <el-alert
        v-else-if="validationResult.certificate?.status === 'available'"
        type="success"
        :closable="false"
        show-icon
        data-test="security-cert-ok"
        title="证书检查通过"
      />
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

const SECRET_REGEX = /^[A-Za-z0-9_-]{1,256}$/;

const props = defineProps({
  secret: {
    type: String,
    default: "",
  },
  certificate: {
    type: String,
    default: "",
  },
  certificateName: {
    type: String,
    default: "",
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
});

const emit = defineEmits([
  "update:secret",
  "update:certificate",
  "update:certificate-name",
  "validate",
]);

const secretValue = computed({
  get() {
    return props.secret;
  },
  set(value) {
    emit("update:secret", value);
  },
});

const certificateDays = computed(
  () => props.validationResult?.certificate?.daysRemaining ?? null,
);

const shouldWarnCertificate = computed(() => {
  if (certificateDays.value === null) return false;
  return certificateDays.value < 30;
});

const conflictList = computed(() => {
  const conflicts = props.validationResult?.secret?.conflicts || [];
  if (!conflicts.length) return "未返回冲突列表";
  return conflicts.join(", ");
});

const secretError = computed(() => {
  if (!secretValue.value) return "";
  if (!SECRET_REGEX.test(secretValue.value)) {
    return "Secret 仅允许字母、数字、下划线或连字符，长度 1-256";
  }
  return "";
});

const handleValidate = () => {
  emit("validate", {
    secret: secretValue.value,
    certificate: props.certificate,
  });
};

const handleCertChange = (uploadFile) => {
  const file = uploadFile?.raw;
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    emit("update:certificate", reader.result || "");
    emit("update:certificate-name", file.name);
  };
  reader.readAsText(file);
};
</script>

<style scoped>
.security-fields {
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  background: var(--color-bg-subtle);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.security-fields header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
}

.security-fields header h4 {
  margin: 0;
}

.security-fields header p {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.security-fields__form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3);
}

.security-fields__hint {
  margin: 4px 0 0;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.security-fields__status {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.security-fields__warning {
  margin: 0;
  font-size: var(--font-size-xs);
}
</style>
