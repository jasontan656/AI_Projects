import { computed, reactive, toRaw, watch } from "vue";
import { ElMessage } from "element-plus";

const createEmptyState = () => ({
  id: null,
  name: "",
  status: "draft",
  nodeSequence: [],
  promptBindings: [],
  strategy: { retryLimit: 2, timeoutMs: 0 },
  metadata: { description: "", tags: [] },
});

const cloneBindings = (bindings = []) =>
  Array.isArray(bindings)
    ? bindings.map((binding) => ({
        nodeId: binding?.nodeId || "",
        promptId: binding?.promptId || null,
      }))
    : [];

const cloneNodeSequence = (sequence = []) =>
  Array.isArray(sequence) ? sequence.filter(Boolean) : [];

const cloneTags = (tags = []) =>
  Array.isArray(tags) ? [...tags] : [];

export function useWorkflowForm(props, emit) {
  const form = reactive(createEmptyState());
  const baseline = reactive(createEmptyState());
  const nodePromptMap = reactive({});
  const errors = reactive({
    name: "",
    nodeSequence: "",
    retryLimit: "",
    timeoutMs: "",
  });

  const resetNodePromptMap = () => {
    Object.keys(nodePromptMap).forEach((key) => delete nodePromptMap[key]);
    (form.promptBindings || []).forEach((binding) => {
      if (binding?.nodeId) {
        nodePromptMap[binding.nodeId] = binding.promptId || null;
      }
    });
  };

  const copyIntoState = (target, source = {}) => {
    target.id = source.id || null;
    target.name = source.name || "";
    target.status = source.status || "draft";
    target.nodeSequence = cloneNodeSequence(source.nodeSequence);
    target.promptBindings = cloneBindings(source.promptBindings);
    target.strategy.retryLimit =
      Number.isFinite(source.strategy?.retryLimit) && source.strategy.retryLimit >= 0
        ? source.strategy.retryLimit
        : 2;
    target.strategy.timeoutMs =
      Number.isFinite(source.strategy?.timeoutMs) && source.strategy.timeoutMs >= 0
        ? source.strategy.timeoutMs
        : 0;
    target.metadata.description = source.metadata?.description || "";
    target.metadata.tags = cloneTags(source.metadata?.tags);
  };

  const copyIntoForm = (source = {}) => {
    copyIntoState(form, source);
    resetNodePromptMap();
    emitDirty();
  };

  const resetBaseline = () => {
    copyIntoState(baseline, form);
  };

  const emitDirty = () => {
    emit("dirty-change", isDirty());
  };

  const updatePromptBindings = () => {
    form.promptBindings = form.nodeSequence.map((nodeId) => ({
      nodeId,
      promptId: nodePromptMap[nodeId] || null,
    }));
    emitDirty();
  };

  const handleSequenceChange = (value = []) => {
    const sanitized = cloneNodeSequence(value);
    form.nodeSequence = sanitized;
    Object.keys(nodePromptMap).forEach((nodeId) => {
      if (!sanitized.includes(nodeId)) {
        delete nodePromptMap[nodeId];
      }
    });
    updatePromptBindings();
  };

  const setNodePrompt = (nodeId, promptId) => {
    if (!nodeId) return;
    nodePromptMap[nodeId] = promptId || null;
    updatePromptBindings();
  };

  const clearNodePrompt = (nodeId) => {
    if (!nodeId) return;
    nodePromptMap[nodeId] = null;
    updatePromptBindings();
  };

  const bulkBindPrompts = (nodeIds = [], promptId = null) => {
    if (!promptId) return;
    const allowed = new Set(form.nodeSequence);
    nodeIds
      .filter((nodeId) => allowed.has(nodeId))
      .forEach((nodeId) => {
        nodePromptMap[nodeId] = promptId;
      });
    updatePromptBindings();
  };

  const resolveNodeName = (nodeId) =>
    props.nodes.find((node) => node.id === nodeId)?.name || nodeId;

  const validateBindings = ({ showMessage = true } = {}) => {
    const nodeSet = new Set(props.nodes.map((node) => node.id));
    const removed = form.nodeSequence.filter((nodeId) => !nodeSet.has(nodeId));
    if (removed.length) {
      form.nodeSequence = form.nodeSequence.filter((nodeId) => nodeSet.has(nodeId));
      removed.forEach((nodeId) => delete nodePromptMap[nodeId]);
      updatePromptBindings();
      if (showMessage) {
        ElMessage.warning(`以下节点已被移除：${removed.join("、")}`);
      }
    }

    const promptSet = new Set(props.prompts.map((prompt) => prompt.id));
    const invalidBindings = Object.entries(nodePromptMap).filter(
      ([, promptId]) => promptId && !promptSet.has(promptId),
    );
    if (invalidBindings.length) {
      invalidBindings.forEach(([nodeId]) => {
        nodePromptMap[nodeId] = null;
      });
      updatePromptBindings();
      if (showMessage) {
        const nodeNames = invalidBindings.map(([nodeId]) => resolveNodeName(nodeId));
        ElMessage.warning(
          `节点 ${nodeNames.join("、")} 的提示词已失效，已自动清除。`,
        );
      }
    }

    if (!form.nodeSequence.length) {
      errors.nodeSequence = "请选择至少一个节点";
      return false;
    }

    errors.nodeSequence = "";
    return removed.length === 0 && invalidBindings.length === 0;
  };

  const validate = () => {
    errors.name = form.name.trim() ? "" : "名称不能为空";
    errors.nodeSequence = form.nodeSequence.length ? "" : "请选择至少一个节点";
    errors.retryLimit =
      form.strategy.retryLimit >= 0 && form.strategy.retryLimit <= 5
        ? ""
        : "重试次数需在 0-5";
    errors.timeoutMs =
      form.strategy.timeoutMs >= 0 ? "" : "超时必须大于等于 0";
    const bindingValid = validateBindings();
    return (
      !errors.name &&
      !errors.nodeSequence &&
      !errors.retryLimit &&
      !errors.timeoutMs &&
      bindingValid
    );
  };

  const canSave = computed(() => {
    if (!form.name.trim()) return false;
    if (!form.nodeSequence.length) return false;
    if (form.strategy.retryLimit < 0 || form.strategy.retryLimit > 5) return false;
    if (form.strategy.timeoutMs < 0) return false;
    const nodeSet = new Set(props.nodes.map((node) => node.id));
    return form.nodeSequence.every((nodeId) => nodeSet.has(nodeId));
  });

  const isDirty = () => {
    const sameName = form.name === baseline.name;
    const sameDesc =
      form.metadata.description === baseline.metadata.description;
    const sameNodes =
      form.nodeSequence.length === baseline.nodeSequence.length &&
      form.nodeSequence.every(
        (nodeId, index) => nodeId === baseline.nodeSequence[index],
      );
    const sameBindings =
      form.promptBindings.length === baseline.promptBindings.length &&
      form.promptBindings.every((binding, index) => {
        const ref = baseline.promptBindings[index] || {};
        return binding.nodeId === ref.nodeId && binding.promptId === ref.promptId;
      });
    const sameStrategy =
      form.strategy.retryLimit === baseline.strategy.retryLimit &&
      form.strategy.timeoutMs === baseline.strategy.timeoutMs;
    return !(sameName && sameDesc && sameNodes && sameBindings && sameStrategy);
  };

  const buildPayload = () => {
    if (!validate()) return null;
    return {
      name: form.name.trim(),
      status: form.status,
      nodeSequence: [...form.nodeSequence],
      promptBindings: form.promptBindings.map((binding) => ({
        nodeId: binding.nodeId,
        promptId: binding.promptId || null,
      })),
      strategy: {
        retryLimit: form.strategy.retryLimit,
        timeoutMs: form.strategy.timeoutMs,
      },
      metadata: {
        description: form.metadata.description,
        tags: [...form.metadata.tags],
      },
    };
  };

  const handleSave = () => buildPayload();

  const handleReset = () => {
    copyIntoForm(baseline);
    emitDirty();
  };

  const updateStrategy = (partial = {}) => {
    if (
      Object.prototype.hasOwnProperty.call(partial, "retryLimit") &&
      partial.retryLimit !== undefined
    ) {
      form.strategy.retryLimit = partial.retryLimit;
    }
    if (
      Object.prototype.hasOwnProperty.call(partial, "timeoutMs") &&
      partial.timeoutMs !== undefined
    ) {
      form.strategy.timeoutMs = partial.timeoutMs;
    }
    emitDirty();
  };

  const getPayload = () =>
    toRaw({
      name: form.name,
      status: form.status,
      nodeSequence: [...form.nodeSequence],
      promptBindings: form.promptBindings.map((binding) => ({ ...binding })),
      strategy: { ...form.strategy },
      metadata: { ...form.metadata },
    });

  watch(
    () => props.workflow,
    (next) => {
      copyIntoForm(next || {});
      resetBaseline();
    },
    { immediate: true, deep: true },
  );

  watch(
    () => props.nodes.map((node) => node.id),
    () => {
      if (form.nodeSequence.length) {
        validateBindings({ showMessage: true });
      }
    },
  );

  watch(
    () => props.prompts.map((prompt) => prompt.id),
    () => {
      if (form.nodeSequence.length) {
        validateBindings({ showMessage: true });
      }
    },
  );

  watch(
    () => [
      form.name,
      form.metadata.description,
      form.nodeSequence.slice(),
      form.promptBindings.map((binding) => `${binding.nodeId}:${binding.promptId}`),
      form.strategy.retryLimit,
      form.strategy.timeoutMs,
    ],
    () => emitDirty(),
    { deep: true },
  );

  return {
    form,
    errors,
    nodePromptMap,
    canSave,
    handleSequenceChange,
    setNodePrompt,
    clearNodePrompt,
    bulkBindPrompts,
    updateStrategy,
    handleReset,
    handleSave,
    isDirty,
    getPayload,
  };
}
