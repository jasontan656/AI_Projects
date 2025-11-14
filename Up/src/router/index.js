import { createRouter, createWebHistory } from "vue-router";

import WorkspaceShell from "../layouts/WorkspaceShell.vue";
import NodesView from "../views/workspace/NodesView.vue";
import PromptsView from "../views/workspace/PromptsView.vue";
import WorkflowView from "../views/workspace/WorkflowView.vue";
import VariablesView from "../views/workspace/VariablesView.vue";
import LogsView from "../views/workspace/LogsView.vue";
import SettingsView from "../views/workspace/SettingsView.vue";

const workspaceChildren = [
  {
    path: "",
    redirect: { name: "WorkspaceNodes" },
  },
  {
    path: "nodes",
    name: "WorkspaceNodes",
    component: NodesView,
  },
  {
    path: "prompts",
    name: "WorkspacePrompts",
    component: PromptsView,
  },
  {
    path: "workflow",
    name: "WorkspaceWorkflow",
    component: WorkflowView,
  },
  {
    path: "variables",
    name: "WorkspaceVariables",
    component: VariablesView,
  },
  {
    path: "logs",
    name: "WorkspaceLogs",
    component: LogsView,
  },
  {
    path: "settings",
    name: "WorkspaceSettings",
    component: SettingsView,
  },
];

const routes = [
  {
    path: "/workspace",
    component: WorkspaceShell,
    children: workspaceChildren,
  },
  {
    path: "/pipelines",
    redirect: "/workspace/nodes",
  },
  {
    path: "/",
    redirect: "/workspace/nodes",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
