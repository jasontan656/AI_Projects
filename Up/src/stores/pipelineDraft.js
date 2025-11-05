import { defineStore } from "pinia";

import {
  cloneActions,
  normalizeActions,
} from "../utils/nodeActions";

const createInitialState = () => ({
  nodes: [],
  selectedNodeId: null,
});

const prepareNodeDraft = (node = {}) => {
  const actions = normalizeActions(node.actions, node.systemPrompt);
  return {
    ...node,
    actions,
  };
};

export const usePipelineDraftStore = defineStore("pipelineDraft", {
  state: () => createInitialState(),
  getters: {
    nodeCount: (state) => state.nodes.length,
    selectedNode: (state) =>
      state.nodes.find((node) => node.id === state.selectedNodeId) || null,
  },
  actions: {
    replaceNodes(nodes = []) {
      this.nodes = nodes.map((node) => prepareNodeDraft(node));
      if (this.selectedNodeId) {
        const stillExists = this.nodes.some(
          (node) => node.id === this.selectedNodeId
        );
        if (!stillExists) {
          this.selectedNodeId = null;
        }
      }
    },
    addNodeDraft(node) {
      if (!node || !node.id) {
        throw new Error("Invalid node payload: missing id");
      }
      const prepared = prepareNodeDraft(node);
      const exists = this.nodes.some((existing) => existing.id === node.id);
      if (exists) {
        this.nodes = this.nodes.map((existing) =>
          existing.id === node.id ? prepared : existing
        );
        return;
      }
      this.nodes.push(prepared);
    },
    removeNodeDraft(nodeId) {
      this.nodes = this.nodes.filter((node) => node.id !== nodeId);
      if (this.selectedNodeId === nodeId) {
        this.selectedNodeId = null;
      }
    },
    setSelectedNode(nodeId) {
      this.selectedNodeId = nodeId;
    },
    resetSelection() {
      this.selectedNodeId = null;
    },
    reset() {
      this.$reset();
    },
    cloneSelectedActions() {
      const node = this.selectedNode;
      return node ? cloneActions(node.actions) : [];
    },
  },
});
