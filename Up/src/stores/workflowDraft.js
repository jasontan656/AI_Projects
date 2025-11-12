import { defineStore } from "pinia";
import {
  fetchWorkflowList,
  fetchWorkflowDetail,
  saveWorkflowDraft,
  removeWorkflowDraft,
  publishWorkflowDraft,
  rollbackWorkflowDraft,
} from "../services/workflowDraftService";
import { createWorkflowDraft } from "../schemas/workflowDraft";

export const useWorkflowDraftStore = defineStore("workflowDraft", {
  state: () => ({
    workflows: [],
    selectedWorkflowId: null,
    currentWorkflow: createWorkflowDraft(),
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
    setCurrentWorkflow(workflow) {
      this.currentWorkflow = createWorkflowDraft(workflow);
      this.history = Array.isArray(this.currentWorkflow.history)
        ? this.currentWorkflow.history
        : [];
    },
    async fetchList(params = {}) {
      this.listLoading = true;
      this.setError("");
      try {
        const { items } = await fetchWorkflowList(params);
        this.workflows = items;
        if (!this.selectedWorkflowId && items[0]?.id) {
          await this.selectWorkflow(items[0].id);
        } else if (this.selectedWorkflowId) {
          const exists = items.some(
            (item) => item.id === this.selectedWorkflowId
          );
          if (!exists) {
            this.selectedWorkflowId = null;
            this.setCurrentWorkflow(createWorkflowDraft());
          }
        }
        if (!this.selectedWorkflowId && !items.length) {
          this.setCurrentWorkflow(createWorkflowDraft());
        }
      } catch (error) {
        this.setError(error.message || "加载 workflow 列表失败");
        throw error;
      } finally {
        this.listLoading = false;
      }
    },
    async selectWorkflow(workflowId) {
      if (!workflowId) {
        this.selectedWorkflowId = null;
        this.setCurrentWorkflow(createWorkflowDraft());
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
        const workflow = await fetchWorkflowDetail(workflowId);
        this.setCurrentWorkflow(workflow);
      } catch (error) {
        this.setError(error.message || "加载 workflow 详情失败");
        throw error;
      } finally {
        this.detailLoading = false;
      }
    },
    startNewWorkflow() {
      this.selectedWorkflowId = null;
      this.setCurrentWorkflow(createWorkflowDraft());
    },
    async saveCurrentWorkflow(payload) {
      this.saving = true;
      this.setError("");
      try {
        const saved = await saveWorkflowDraft(this.currentWorkflow, payload);
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
          this.setCurrentWorkflow(saved);
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
        await removeWorkflowDraft(workflowId);
        this.workflows = this.workflows.filter((item) => item.id !== workflowId);
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
        const published = await publishWorkflowDraft(
          this.selectedWorkflowId,
          meta
        );
        this.setCurrentWorkflow(published);
        this.workflows = this.workflows.map((item) =>
          item.id === published.id ? published : item
        );
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
        const rolled = await rollbackWorkflowDraft(
          this.selectedWorkflowId,
          version
        );
        this.setCurrentWorkflow(rolled);
        this.workflows = this.workflows.map((item) =>
          item.id === rolled.id ? rolled : item
        );
        return rolled;
      } catch (error) {
        this.setError(error.message || "回滚失败");
        throw error;
      } finally {
        this.rollingBack = false;
      }
    },
  },
});
