export const WORKFLOW_STATUSES = ["draft", "published"];

const COVERAGE_DEFAULT = {
  status: "unknown",
  updatedAt: null,
  scenarios: [],
  mode: "webhook",
  lastRunId: null,
  lastError: null,
  actorId: null,
};

const WORKFLOW_DEFAULT = {
  id: null,
  name: "",
  status: "draft",
  version: 0,
  nodeSequence: [],
  promptBindings: [],
  strategy: { retryLimit: 2, timeoutMs: 0 },
  metadata: { description: "", tags: [] },
  history: [],
  testCoverage: COVERAGE_DEFAULT,
};

const asArray = (value) => (Array.isArray(value) ? value : []);

const normalizeNodeSequence = (sequence) =>
  asArray(sequence).filter((id) => Boolean(id));

const normalizePromptBindings = (bindings, nodeSequence) => {
  const nodeSet = new Set(nodeSequence);
  return asArray(bindings)
    .filter((binding) => binding?.nodeId && nodeSet.has(binding.nodeId))
    .map((binding) => ({
      nodeId: binding.nodeId,
      promptId: binding.promptId || null,
    }));
};

export function createWorkflowDraft(overrides = {}) {
  const normalizedNodeSequence = normalizeNodeSequence(overrides.nodeSequence);
  return {
    ...WORKFLOW_DEFAULT,
    ...overrides,
    strategy: {
      ...WORKFLOW_DEFAULT.strategy,
      ...(overrides.strategy || {}),
    },
    metadata: {
      ...WORKFLOW_DEFAULT.metadata,
      ...(overrides.metadata || {}),
    },
    nodeSequence: normalizedNodeSequence,
    promptBindings: normalizePromptBindings(
      overrides.promptBindings,
      normalizedNodeSequence
    ),
    history: asArray(overrides.history),
    testCoverage: normalizeCoverage(overrides.testCoverage),
  };
}

export function normalizeWorkflowEntity(entity) {
  if (!entity) {
    return createWorkflowDraft();
  }
  const id = entity.id || entity.workflowId || null;
  return createWorkflowDraft({
    ...entity,
    id,
  });
}

export function buildWorkflowPayload(payload = {}) {
  const nodeSequence = normalizeNodeSequence(payload.nodeSequence);
  if (!nodeSequence.length) {
    throw new Error("WORKFLOW_NODE_REQUIRED");
  }
  const promptBindings = normalizePromptBindings(
    payload.promptBindings,
    nodeSequence
  );
  const strategy = {
    retryLimit: Number.isFinite(payload.strategy?.retryLimit)
      ? payload.strategy.retryLimit
      : WORKFLOW_DEFAULT.strategy.retryLimit,
    timeoutMs: Number.isFinite(payload.strategy?.timeoutMs)
      ? payload.strategy.timeoutMs
      : WORKFLOW_DEFAULT.strategy.timeoutMs,
  };
  const metadata = {
    description: payload.metadata?.description || "",
    tags: asArray(payload.metadata?.tags),
  };
  return {
    name: (payload.name || "").trim(),
    status: WORKFLOW_STATUSES.includes(payload.status)
      ? payload.status
      : WORKFLOW_DEFAULT.status,
    nodeSequence,
    promptBindings,
    strategy,
    metadata,
  };
}

function normalizeCoverage(coverage = null) {
  if (!coverage) {
    return { ...COVERAGE_DEFAULT };
  }
  return {
    ...COVERAGE_DEFAULT,
    ...coverage,
    scenarios: asArray(coverage.scenarios),
    updatedAt: coverage.updatedAt || null,
  };
}
