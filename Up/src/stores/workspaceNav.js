import { defineStore } from "pinia";

const NAV_ITEMS = [
  {
    id: "nodes",
    label: "Nodes",
    title: "节点操作",
    description: "维护节点元数据与动作脚本，生成 pipeline 契约。",
  },
  {
    id: "prompts",
    label: "Prompts",
    title: "提示词管理",
    description: "创建与维护 Markdown 模板，并同步到 Workflow 套件。",
  },
  {
    id: "workflow",
    label: "Workflow",
    title: "Workflow 编排",
    description: "组合节点与提示词，配置执行顺序与发布设置。",
  },
  {
    id: "variables",
    label: "Variables",
    title: "变量管理",
    description: "集中维护运行时变量，协调跨节点依赖。",
  },
  {
    id: "logs",
    label: "Logs",
    title: "实时日志",
    description: "通过 SSE/WS 订阅执行轨迹并追踪告警。",
  },
  {
    id: "settings",
    label: "Settings",
    title: "设置（Soon）",
    description: "配置 Workspace 偏好、集成与即将上线的功能。",
    soon: true,
  },
];

export const WORKSPACE_TAB_ROUTE_MAP = {
  nodes: "WorkspaceNodes",
  prompts: "WorkspacePrompts",
  workflow: "WorkspaceWorkflow",
  variables: "WorkspaceVariables",
  logs: "WorkspaceLogs",
  settings: "WorkspaceSettings",
};

export const useWorkspaceNavStore = defineStore("workspaceNav", {
  state: () => ({
    activeTab: "nodes",
    navHistory: [],
    logsConnected: false,
    guards: {},
    workflowBlockedReason: "",
  }),
  getters: {
    navItems: () => NAV_ITEMS,
    currentNav(state) {
      return NAV_ITEMS.find((item) => item.id === state.activeTab) ?? NAV_ITEMS[0];
    },
  },
  actions: {
    setActiveTab(tabId) {
      if (!WORKSPACE_TAB_ROUTE_MAP[tabId]) {
        return;
      }
      this.activeTab = tabId;
    },
    recordNavigation(tabId, meta = {}) {
      this.navHistory = [
        ...this.navHistory,
        {
          tabId,
          at: new Date().toISOString(),
          ...meta,
        },
      ].slice(-200);
    },
    markLogsConnection(status) {
      this.logsConnected = Boolean(status);
    },
    setWorkflowBlocked(reason = "") {
      this.workflowBlockedReason = reason || "";
    },
    registerGuard(tabId, guardFn) {
      if (!WORKSPACE_TAB_ROUTE_MAP[tabId]) {
        return () => {};
      }
      this.guards[tabId] = guardFn;
      return () => {
        if (this.guards[tabId] === guardFn) {
          delete this.guards[tabId];
        }
      };
    },
    async ensureCanLeave(tabId) {
      const guard = this.guards[tabId];
      if (!guard) {
        return true;
      }
      try {
        const result = await guard();
        return result !== false;
      } catch (error) {
        console.warn("[workspaceNav] guard rejected", error);
        return false;
      }
    },
    $reset() {
      this.activeTab = "nodes";
      this.navHistory = [];
      this.logsConnected = false;
      this.guards = {};
      this.workflowBlockedReason = "";
    },
  },
});
