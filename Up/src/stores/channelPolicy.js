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
  }),
  getters: {
    isBound: (state) =>
      Boolean(
        state.policy?.workflowId &&
          (state.policy?.botToken || state.policy?.maskedBotToken)
      ),
    cooldownUntil: (state) => getTestCooldownUntil(state.testThrottle),
    healthPollingPaused: (state) => state.healthState.paused,
  },
  actions: {
    setPolicy(data) {
      this.policy = createChannelPolicy(data);
    },
    resetPolicy() {
      this.policy = createChannelPolicy();
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
  },
});
