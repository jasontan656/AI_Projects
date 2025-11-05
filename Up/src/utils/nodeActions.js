import { v4 as uuid } from "uuid";

export const ACTION_TYPES = {
  PROMPT_APPEND: "prompt_append",
  TOOL_INVOKE: "tool_invoke",
  EMIT_OUTPUT: "emit_output",
};

const templateToken = (templateId) => `{{template:${templateId}}}`;

const ALLOWED_CONFIG_KEYS = ["templateId", "legacyText", "inputMapping", "disabled"];

const sanitizeConfig = (config = {}) =>
  ALLOWED_CONFIG_KEYS.reduce((acc, key) => {
    if (config[key] !== undefined) {
      acc[key] = config[key];
    }
    return acc;
  }, {});

export const createPromptAppendAction = ({
  templateId = null,
  legacyText = "",
  order = 0,
} = {}) => ({
  id: uuid(),
  type: ACTION_TYPES.PROMPT_APPEND,
  config: sanitizeConfig({
    templateId,
    legacyText,
  }),
  order,
});

export const cloneActions = (actions = []) =>
  actions.map((action) => ({
    ...action,
    config: sanitizeConfig(action.config || {}),
  }));

const normalizeSingleAction = (action, fallbackOrder = 0) => ({
  id: action.id || uuid(),
  type: action.type || ACTION_TYPES.PROMPT_APPEND,
  config: sanitizeConfig(action.config || {}),
  order: action.order ?? fallbackOrder,
  disabled: action.disabled || false,
});

const buildActionsFromSystemPrompt = (systemPrompt) => {
  const text = (systemPrompt || "").trim();
  if (!text) {
    return [];
  }
  return [createPromptAppendAction({ legacyText: text, order: 0 })];
};

export const normalizeActions = (rawActions, systemPrompt) => {
  const hasValidActions = Array.isArray(rawActions) && rawActions.length > 0;
  const baseActions = hasValidActions
    ? rawActions.map((action, index) => normalizeSingleAction(action, index))
    : buildActionsFromSystemPrompt(systemPrompt);

  return baseActions
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .map((action, index) => ({ ...action, order: index }));
};

export const serializeActionsForApi = (actions = []) =>
  actions.map((action, index) => ({
    id: action.id,
    type: action.type,
    order: index,
    config: sanitizeConfig(action.config || {}),
  }));

export const composeSystemPromptFromActions = (actions = []) => {
  const parts = [];

  actions
    .filter((action) => action.type === ACTION_TYPES.PROMPT_APPEND)
    .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    .forEach((action) => {
      const { templateId, legacyText } = action.config || {};
      if (legacyText && legacyText.trim()) {
        parts.push(legacyText.trim());
      } else if (templateId) {
        parts.push(templateToken(templateId));
      }
    });

  return parts.join("\n\n");
};

export const hasPromptActions = (actions = []) =>
  actions.some((action) => action.type === ACTION_TYPES.PROMPT_APPEND);
