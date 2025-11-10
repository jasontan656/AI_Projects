import { defineStore } from "pinia";

import {
  listWorkflows,
  getWorkflow,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  publishWorkflow,
  rollbackWorkflow,
} from "../services/workflowService";

const createEmptyWorkflow = () => ({
  id: null,
  name: "",
  status: "draft",
  version: 0,
  nodeSequence: [],
  promptBindings: [],
  strategy: { retryLimit: 0, timeoutMs: 0 },
  metadata: { description: "", tags: [] },
  history: [],
});

export const useWorkflowDraftStore = defineStore("workflowDraft", {
  state: () => ({
    workflows: [],
    selectedWorkflowId: null,
    currentWorkflow: createEmptyWorkflow(),
    history: [],
    listLoading: false,
    detailLoading: false,
    saving: false,
    deleting: false,
    publishing: false,
    rollingBack: false,
    error: "",
  }),
  getters: {
    hasSelection: (state) => Boolean(state.selectedWorkflowId),
  },
  actions: {
    setError(message) {
      this.error = message || "";
    },
    async fetchList(params = {}) {
      this.listLoading = true;
      this.setError("");
      try {
        const data = await listWorkflows(params);
        const items = Array.isArray(data?.items) ? data.items : [];
        this.workflows = items;
        if (!this.selectedWorkflowId && items[0]?.id) {
          await this.selectWorkflow(items[0].id);
        }
        if (this.selectedWorkflowId) {
          const stillExists = items.some(
            (item) => item.id === this.selectedWorkflowId
          );
          if (!stillExists) {
            this.selectedWorkflowId = null;
            this.currentWorkflow = createEmptyWorkflow();
          }
        }
        if (!this.selectedWorkflowId && !items.length) {
          this.currentWorkflow = createEmptyWorkflow();
        }
      } catch (error) {
        this.setError(error.message || "加载 workflow 列表失败");
      } finally {
        this.listLoading = false;
      }
    },
    async selectWorkflow(workflowId) {
      if (!workflowId) {
        this.selectedWorkflowId = null;
        this.currentWorkflow = createEmptyWorkflow();
        this.history = [];
        return;
      }
      this.selectedWorkflowId = workflowId;
      await this.loadWorkflow(workflowId);
    },
    async loadWorkflow(workflowId) {
      if (!workflowId) return;
      this.detailLoading = true;
      this.setError("");
      try {
        const data = await getWorkflow(workflowId);
        if (data) {
          this.currentWorkflow = {
            history: data.history || [],
            ...data,
          };
          this.history = Array.isArray(data.history) ? data.history : [];
        }
      } catch (error) {
        this.setError(error.message || "加载 workflow 详情失败");
      } finally {
        this.detailLoading = false;
      }
    },
    startNewWorkflow() {
      this.selectedWorkflowId = null;
      this.currentWorkflow = createEmptyWorkflow();
      this.history = [];
    },
    async saveCurrentWorkflow(payload) {
      this.saving = true;
      this.setError("");
      try {
        if (!Array.isArray(payload?.nodeSequence) || payload.nodeSequence.length === 0) {
          throw new Error("WORKFLOW_NODE_REQUIRED");
        }

        let saved;
        if (this.currentWorkflow.id) {
          saved = await updateWorkflow(this.currentWorkflow.id, payload);
        } else {
          saved = await createWorkflow(payload);
        }
        if (saved?.id) {
          const exists = this.workflows.some((item) => item.id === saved.id);
          if (exists) {
            this.workflows = this.workflows.map((item) =>
              item.id === saved.id ? saved : item
            );
          } else {
            this.workflows = [saved, ...this.workflows];
          }
          this.selectedWorkflowId = saved.id;
          this.currentWorkflow = { history: saved.history || [], ...saved };
        }
        return saved;
      } catch (error) {
        if (error?.message === "WORKFLOW_NODE_REQUIRED") {
          this.setError("Workflow 需要至少一个节点");
        } else {
          this.setError(error?.message || "保存 workflow 失败");
        }
        throw error;
      } finally {
        this.saving = false;
      }
    },
    async deleteWorkflow(workflowId) {
      if (!workflowId) return;
      this.deleting = true;
      this.setError("");
      try {
        await deleteWorkflow(workflowId);
        this.workflows = this.workflows.filter(
          (item) => item.id !== workflowId
        );
        if (this.selectedWorkflowId === workflowId) {
          const fallback = this.workflows[0];
          if (fallback?.id) {
            await this.selectWorkflow(fallback.id);
          } else {
            this.startNewWorkflow();
          }
        }
      } catch (error) {
        this.setError(error.message || "删除 workflow 失败");
        throw error;
      } finally {
        this.deleting = false;
      }
    },
    async publishSelected(meta = {}) {
      if (!this.selectedWorkflowId) {
        throw new Error("请选择 workflow");
      }
      this.publishing = true;
      this.setError("");
      try {
        const published = await publishWorkflow(this.selectedWorkflowId, meta);
        if (published) {
          this.currentWorkflow = {
            history: published.history || [],
            ...published,
          };
          this.history = Array.isArray(published.history)
            ? published.history
            : [];
          this.workflows = this.workflows.map((item) =>
            item.id === published.id ? published : item
          );
        }
        return published;
      } catch (error) {
        this.setError(error.message || "发布失败");
        throw error;
      } finally {
        this.publishing = false;
      }
    },
    async rollbackSelected(version) {
      if (!this.selectedWorkflowId) {
        throw new Error("请选择 workflow");
      }
      this.rollingBack = true;
      this.setError("");
      try {
        const rolledBack = await rollbackWorkflow(
          this.selectedWorkflowId,
          version
        );
        if (rolledBack) {
          this.currentWorkflow = {
            history: rolledBack.history || [],
            ...rolledBack,
          };
          this.history = Array.isArray(rolledBack.history)
            ? rolledBack.history
            : [];
          this.workflows = this.workflows.map((item) =>
            item.id === rolledBack.id ? rolledBack : item
          );
        }
        return rolledBack;
      } catch (error) {
        this.setError(error.message || "回滚失败");
        throw error;
      } finally {
        this.rollingBack = false;
      }
    },
  },
});
