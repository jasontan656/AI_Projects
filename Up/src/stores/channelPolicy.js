import { defineStore } from "pinia";

import {
  getChannelPolicy,
  saveChannelPolicy,
  deleteChannelPolicy,
  fetchChannelHealth,
  sendChannelTest,
} from "../services/channelService";

const createEmptyPolicy = () => ({
  workflowId: null,
  channel: "telegram",
  botToken: "",
  maskedBotToken: "",
  webhookUrl: "",
  waitForResult: true,
  workflowMissingMessage: "",
  timeoutMessage: "",
  metadata: {
    allowedChatIds: [],
    rateLimitPerMin: 60,
    locale: "zh-CN",
  },
  updatedAt: null,
  updatedBy: null,
});

export const useChannelPolicyStore = defineStore("channelPolicy", {
  state: () => ({
    policy: createEmptyPolicy(),
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
    pollTimer: null,
    pollIntervalMs: 30000,
    failureCount: 0,
    frequencyWindow: [],
  }),
  getters: {
    isBound: (state) =>
      Boolean(
        state.policy?.workflowId &&
          (state.policy?.botToken || state.policy?.maskedBotToken)
      ),
  },
  actions: {
    setPolicy(data) {
      const empty = createEmptyPolicy();
      const masked = data?.maskedBotToken || "";
      this.policy = {
        ...empty,
        ...data,
        botToken: data?.botToken || masked,
        maskedBotToken: masked,
        metadata: {
          ...empty.metadata,
          ...(data?.metadata || {}),
        },
      };
    },
    resetPolicy() {
      this.policy = createEmptyPolicy();
    },
    stopPolling() {
      if (this.pollTimer) {
        clearTimeout(this.pollTimer);
        this.pollTimer = null;
      }
    },
    async fetchPolicy(workflowId) {
      if (!workflowId) {
        this.resetPolicy();
        return;
      }
      this.loading = true;
      this.policyError = "";
      try {
        const policy = await getChannelPolicy(workflowId);
        if (policy) {
          this.setPolicy(policy);
        } else {
          this.resetPolicy();
        }
      } catch (error) {
        if ((error.message || "").includes("404")) {
          this.resetPolicy();
        } else {
          this.policyError = error.message || "加载渠道配置失败";
        }
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
      } catch (error) {
        this.policyError = error.message || "解绑渠道失败";
        throw error;
      } finally {
        this.deleting = false;
      }
    },
    async fetchHealth(workflowId, { silent = false } = {}) {
      if (!workflowId) return;
      if (!silent) {
        this.healthLoading = true;
      }
      this.healthError = "";
      try {
        const data = await fetchChannelHealth(workflowId);
        this.health = data;
        this.failureCount = 0;
        if (!silent) {
          this.healthLoading = false;
        }
        this.scheduleNextPoll(workflowId, true);
      } catch (error) {
        this.healthError = error.message || "健康检查失败";
        this.failureCount += 1;
        if (!silent) {
          this.healthLoading = false;
        }
        this.scheduleNextPoll(workflowId, false);
      }
    },
    scheduleNextPoll(workflowId, success) {
      this.stopPolling();
      if (!workflowId) return;
      if (!success && this.failureCount >= 3) {
        return;
      }
      const base = 30000;
      const interval = success
        ? base
        : Math.min(base * Math.pow(2, this.failureCount - 1), 120000);
      this.pollIntervalMs = interval;
      this.pollTimer = setTimeout(() => {
        this.fetchHealth(workflowId, { silent: true });
      }, interval);
    },
    recordTestResult(result) {
      const items = [{ ...result }, ...this.testHistory];
      this.testHistory = items.slice(0, 10);
    },
    cleanupFrequencyWindow(now = Date.now()) {
      this.frequencyWindow = this.frequencyWindow.filter(
        (timestamp) => now - timestamp < 60000
      );
    },
    canSendTest(now = Date.now()) {
      this.cleanupFrequencyWindow(now);
      return this.frequencyWindow.length < 3;
    },
    markTestSent(now = Date.now()) {
      this.frequencyWindow = [...this.frequencyWindow, now];
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
