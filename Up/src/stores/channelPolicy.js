import { defineStore } from "pinia";
import {
  CHANNEL_HEALTH_DEFAULTS,
  createChannelPolicy,
  createTestThrottleState,
  getTestCooldownUntil,
  canSendTest,
  recordTestAttempt,
} from "../schemas/channelPolicy.js";
import {
  fetchChannelPolicy,
  saveChannelPolicy,
  deleteChannelPolicy,
  fetchChannelHealth,
  sendChannelTest,
  runCoverageTests,
  validateWebhookSecurity,
} from "../services/channelPolicyClient";
import { createChannelHealthScheduler } from "../services/channelHealthScheduler";

const TEST_HISTORY_LIMIT = 10;

export const useChannelPolicyStore = defineStore("channelPolicy", {
  state: () => ({
    policy: createChannelPolicy(),
    health: null,
    testHistory: [],
    loading: false,
    saving: false,
    deleting: false,
    testing: false,
    healthLoading: false,
    healthError: "",
    policyError: "",
    testError: "",
    healthState: {
      paused: false,
      failureCount: 0,
      nextInterval: CHANNEL_HEALTH_DEFAULTS.baseIntervalMs,
    },
    testThrottle: createTestThrottleState(),
    coverageStatus: "unknown",
    coverageUpdatedAt: null,
    coverageScenarios: [],
    coverageMode: "webhook",
    coverageLastError: "",
    coverageLoading: false,
    coverageError: "",
    securitySnapshot: null,
    securityChecking: false,
    securityError: "",
    securityBlockingMessage: "",
  }),
  getters: {
    isBound: (state) =>
      Boolean(
        state.policy?.workflowId &&
          (state.policy?.botToken || state.policy?.maskedBotToken)
      ),
    cooldownUntil: (state) => getTestCooldownUntil(state.testThrottle),
    healthPollingPaused: (state) => state.healthState.paused,
    coverage: (state) => ({
      status: state.coverageStatus,
      updatedAt: state.coverageUpdatedAt,
      scenarios: state.coverageScenarios,
      mode: state.coverageMode,
      lastError: state.coverageLastError,
    }),
    isCoverageGreen: (state) => state.coverageStatus === "green",
  },
  actions: {
    setPolicy(data) {
      this.policy = createChannelPolicy(data);
      this.resetSecurityState();
    },
    resetPolicy() {
      this.policy = createChannelPolicy();
      this.setCoverage(null);
      this.resetSecurityState();
    },
    resetSecurityState() {
      this.securitySnapshot = null;
      this.securityChecking = false;
      this.securityError = "";
      this.securityBlockingMessage = "";
    },
    ensureScheduler() {
      if (this._scheduler) {
        return;
      }
      this._scheduler = createChannelHealthScheduler({
        poller: async (workflowId, { silent } = {}) => {
          if (!silent) {
            this.healthLoading = true;
            this.healthError = "";
          }
          try {
            const data = await fetchChannelHealth(workflowId, {
              includeMetrics: true,
            });
            return data;
          } finally {
            if (!silent) {
              this.healthLoading = false;
            }
          }
        },
        baseIntervalMs: CHANNEL_HEALTH_DEFAULTS.baseIntervalMs,
        maxIntervalMs: CHANNEL_HEALTH_DEFAULTS.maxIntervalMs,
        maxFailures: CHANNEL_HEALTH_DEFAULTS.maxFailures,
      });
    },
    updateHealthState() {
      if (!this._scheduler) {
        this.healthState = {
          paused: false,
          failureCount: 0,
          nextInterval: CHANNEL_HEALTH_DEFAULTS.baseIntervalMs,
        };
        return;
      }
      this.healthState = this._scheduler.getState();
    },
    stopPolling() {
      if (this._scheduler) {
        this._scheduler.stop();
      }
      this.updateHealthState();
    },
    startHealthMonitor(workflowId) {
      if (!workflowId) {
        this.stopPolling();
        return;
      }
      this.ensureScheduler();
      this._scheduler.start(workflowId, {
        onSuccess: (data) => {
          this.health = data;
          this.healthError = "";
          this.healthLoading = false;
          this.updateHealthState();
        },
        onFailure: (error) => {
          this.healthError = error?.message || "健康检查失败";
          this.healthLoading = false;
          this.updateHealthState();
        },
        onPause: (error) => {
          this.healthError = error?.message || "健康检查失败";
          this.updateHealthState();
        },
      });
    },
    async fetchPolicy(workflowId) {
      if (!workflowId) {
        this.resetPolicy();
        return;
      }
      this.loading = true;
      this.policyError = "";
      try {
        const policy = await fetchChannelPolicy(workflowId);
        if (policy) {
          this.setPolicy(policy);
        } else {
          this.resetPolicy();
        }
      } catch (error) {
        this.policyError = error.message || "加载渠道配置失败";
        throw error;
      } finally {
        this.loading = false;
      }
    },
    async savePolicy(workflowId, payload) {
      if (!workflowId) {
        throw new Error("workflow 未发布，无法绑定渠道");
      }
      this.saving = true;
      this.policyError = "";
      try {
        const policy = await saveChannelPolicy(workflowId, payload);
        this.setPolicy(policy);
        return policy;
      } catch (error) {
        this.policyError = error.message || "保存渠道配置失败";
        throw error;
      } finally {
        this.saving = false;
      }
    },
    async removePolicy(workflowId) {
      if (!workflowId) return;
      this.deleting = true;
      this.policyError = "";
      try {
        await deleteChannelPolicy(workflowId);
        this.resetPolicy();
        this.stopPolling();
      } catch (error) {
        this.policyError = error.message || "解绑渠道失败";
        throw error;
      } finally {
        this.deleting = false;
      }
    },
    async fetchHealth(workflowId, { silent = false } = {}) {
      if (!workflowId) {
        this.stopPolling();
        return;
      }
      this.startHealthMonitor(workflowId);
      if (this._scheduler) {
        await this._scheduler.refresh({ silent });
        this.updateHealthState();
      }
    },
    recordTestResult(result) {
      const items = [{ ...result }, ...this.testHistory];
      this.testHistory = items.slice(0, TEST_HISTORY_LIMIT);
    },
    canSendTest(now = Date.now()) {
      return canSendTest(this.testThrottle, now);
    },
    markTestSent(timestamp = Date.now()) {
      recordTestAttempt(this.testThrottle, timestamp);
    },
    async sendTest(payload) {
      if (!this.canSendTest()) {
        throw new Error("测试频率超限，请稍后再试");
      }
      this.testing = true;
      this.testError = "";
      const timestamp = Date.now();
      try {
        const result = await sendChannelTest(payload);
        this.markTestSent(timestamp);
        this.recordTestResult({
          ...result,
          status: "success",
          timestamp: new Date().toISOString(),
          chatId: payload.chatId,
        });
        return result;
      } catch (error) {
        this.testError = error.message || "测试失败";
        this.recordTestResult({
          status: "failed",
          error: error.message,
          timestamp: new Date().toISOString(),
          chatId: payload.chatId,
        });
        throw error;
      } finally {
        this.testing = false;
      }
    },
    setCoverage(coverage) {
      if (!coverage) {
        this.coverageStatus = "unknown";
        this.coverageUpdatedAt = null;
        this.coverageScenarios = [];
        this.coverageMode = "webhook";
        this.coverageLastError = "";
        return;
      }
      this.coverageStatus = coverage.status || "unknown";
      this.coverageUpdatedAt = coverage.updatedAt || null;
      this.coverageScenarios = Array.isArray(coverage.scenarios)
        ? coverage.scenarios
        : [];
      this.coverageMode = coverage.mode || "webhook";
      this.coverageLastError = coverage.lastError || "";
    },
    async runCoverageTests(workflowId, payload = {}) {
      if (!workflowId) {
        throw new Error("workflow 未发布，无法触发覆盖测试");
      }
      this.coverageLoading = true;
      this.coverageError = "";
      try {
        const result = await runCoverageTests(workflowId, payload);
        this.setCoverage(result);
        return result;
      } catch (error) {
        this.coverageError = error.message || "触发覆盖测试失败";
        throw error;
      } finally {
        this.coverageLoading = false;
      }
    },
    async validateSecretUniqueness(workflowId, payload = {}) {
      if (!workflowId) {
        throw new Error("workflow 未发布，无法校验 Secret");
      }
      const secretToken = (payload.secret || payload.secretToken || "").trim();
      if (!secretToken) {
        throw new Error("Secret 不能为空");
      }
      this.securityChecking = true;
      this.securityError = "";
      try {
        const result = await validateWebhookSecurity(workflowId, {
          secretToken,
          certificate: payload.certificate || "",
          webhookUrl: payload.webhookUrl || this.policy.webhookUrl,
        });
        this.securitySnapshot = result ?? null;
        const secretState = result?.secret;
        const certificateState = result?.certificate;
        if (secretState && secretState.isUnique === false) {
          const conflicts = Array.isArray(secretState.conflicts)
            ? secretState.conflicts.join(", ")
            : "未知 workflow";
          this.securityBlockingMessage = `Webhook Secret 已被 ${conflicts} 使用`;
        } else if (
          typeof certificateState?.daysRemaining === "number" &&
          certificateState.daysRemaining < 30
        ) {
          this.securityBlockingMessage = "证书将在 30 天内到期，请尽快更换";
        } else {
          this.securityBlockingMessage = "";
        }
        return result;
      } catch (error) {
        this.securityError = error.message || "Secret/TLS 校验失败";
        this.securityBlockingMessage = this.securityError;
        throw error;
      } finally {
        this.securityChecking = false;
      }
    },
  },
});
