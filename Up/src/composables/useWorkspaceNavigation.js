import { inject } from "vue";

export const workspaceNavigationSymbol = Symbol("WorkspaceNavigation");

export const useWorkspaceNavigation = () => inject(workspaceNavigationSymbol, null);
