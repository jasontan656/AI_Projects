<template>
  <div ref="editorRoot" class="prompt-code-editor"></div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { EditorState, Compartment } from "@codemirror/state";
import {
  EditorView,
  keymap,
  highlightActiveLine,
  highlightActiveLineGutter,
  lineNumbers,
  placeholder as cmPlaceholder,
} from "@codemirror/view";
import { history, historyKeymap } from "@codemirror/commands";
import { defaultHighlightStyle, syntaxHighlighting } from "@codemirror/language";
import { markdown } from "@codemirror/lang-markdown";
import { json } from "@codemirror/lang-json";
import { yaml } from "@codemirror/lang-yaml";

const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
  language: {
    type: String,
    default: "markdown",
  },
  placeholder: {
    type: String,
    default: "",
  },
  readonly: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["update:modelValue"]);

const editorRoot = ref(null);
let view = null;
const languageCompartment = new Compartment();
const readOnlyCompartment = new Compartment();
const placeholderCompartment = new Compartment();

const resolveLanguage = computed(() => {
  switch ((props.language || "markdown").toLowerCase()) {
    case "yaml":
      return yaml();
    case "json":
      return json();
    default:
      return markdown();
  }
});

const baseTheme = EditorView.theme({
  "&": {
    border: "1px solid var(--color-border-strong)",
    borderRadius: "var(--radius-xs)",
    backgroundColor: "var(--color-bg-panel)",
    fontFamily:
      "var(--font-family-mono, 'Fira Code', 'SFMono-Regular', Menlo, Monaco, Consolas, 'Courier New', monospace)",
    fontSize: "var(--font-size-sm)",
  },
  ".cm-content": {
    padding: "var(--space-2)",
  },
  ".cm-scroller": {
    fontFamily: "inherit",
  },
  ".cm-placeholder": {
    color: "var(--color-text-tertiary)",
  },
});

const createState = () =>
  EditorState.create({
    doc: props.modelValue ?? "",
    extensions: [
      lineNumbers(),
      highlightActiveLineGutter(),
      history(),
      highlightActiveLine(),
      keymap.of([...historyKeymap]),
      languageCompartment.of(resolveLanguage.value),
      readOnlyCompartment.of(EditorState.readOnly.of(Boolean(props.readonly))),
      placeholderCompartment.of(props.placeholder ? cmPlaceholder(props.placeholder) : []),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      baseTheme,
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          const value = update.state.doc.toString();
          emit("update:modelValue", value);
        }
      }),
    ],
  });

onMounted(() => {
  if (!editorRoot.value) return;
  view = new EditorView({
    state: createState(),
    parent: editorRoot.value,
  });
});

onBeforeUnmount(() => {
  if (view) {
    view.destroy();
    view = null;
  }
});

watch(
  () => props.modelValue,
  (value) => {
    if (!view) return;
    const current = view.state.doc.toString();
    if (value !== current) {
      view.dispatch({
        changes: { from: 0, to: current.length, insert: value ?? "" },
      });
    }
  }
);

watch(
  () => props.language,
  () => {
    if (!view) return;
    view.dispatch({
      effects: languageCompartment.reconfigure(resolveLanguage.value),
    });
  }
);

watch(
  () => props.readonly,
  (readonly) => {
    if (!view) return;
    view.dispatch({
      effects: readOnlyCompartment.reconfigure(EditorState.readOnly.of(Boolean(readonly))),
    });
  }
);

watch(
  () => props.placeholder,
  (text) => {
    if (!view) return;
    const extension = text ? cmPlaceholder(text) : [];
    view.dispatch({
      effects: placeholderCompartment.reconfigure(extension),
    });
  }
);
</script>

<style scoped>
.prompt-code-editor {
  width: 100%;
  min-height: 320px;
}

.prompt-code-editor :deep(.cm-editor) {
  height: 100%;
}

.prompt-code-editor :deep(.cm-scroller) {
  overflow: auto;
  font-family: inherit;
}
</style>
