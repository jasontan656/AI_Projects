import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { usePipelineDraftStore } from "../../src/stores/pipelineDraft";

const sampleNode = () => ({
  id: "node_test",
  name: "测试节点",
  allowLLM: true,
  systemPrompt: "system prompt",
  createdAt: "2025-11-04T00:00:00.000Z",
});

describe("pipelineDraft store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("adds a node draft", () => {
    const store = usePipelineDraftStore();
    const node = sampleNode();

    store.addNodeDraft(node);

    expect(store.nodes).toHaveLength(1);
    expect(store.nodes[0]).toMatchObject(node);
  });

  it("removes a node draft", () => {
    const store = usePipelineDraftStore();
    const node = sampleNode();

    store.addNodeDraft(node);
    store.removeNodeDraft(node.id);

    expect(store.nodes).toHaveLength(0);
  });
});
