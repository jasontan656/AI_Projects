import { createRequire } from "module";
import { vi } from "vitest";

const require = createRequire(import.meta.url);
const { config } = require("@vue/test-utils");

const passthrough = {
  template: "<div><slot /></div>",
};

const clickable = {
  emits: ["click"],
  template: "<button type=\"button\" @click=\"$emit('click', $event)\"><slot /></button>",
};

config.global.stubs = {
  ...(config.global.stubs || {}),
  ElContainer: passthrough,
  ElAside: passthrough,
  ElHeader: passthrough,
  ElMain: passthrough,
  ElTabs: {
    props: ["modelValue"],
    emits: ["update:modelValue"],
    template: "<div data-testid=\"el-tabs\"><slot /></div>",
  },
  ElTabPane: passthrough,
  ElForm: passthrough,
  ElFormItem: passthrough,
  ElInput: {
    props: ["modelValue"],
    emits: ["update:modelValue"],
    template:
      "<input :value=\"modelValue\" data-testid=\"el-input\" @input=\"$emit('update:modelValue', $event.target.value)\" />",
  },
  ElInputNumber: {
    props: ["modelValue"],
    emits: ["update:modelValue"],
    template:
      "<input type=\"number\" :value=\"modelValue\" data-testid=\"el-input-number\" @input=\"$emit('update:modelValue', Number($event.target.value))\" />",
  },
  ElSelect: passthrough,
  ElOption: passthrough,
  ElPopover: passthrough,
  ElMenu: passthrough,
  ElMenuItem: {
    props: ["index"],
    emits: ["click"],
    template:
      "<button type=\"button\" :data-index=\"index\" data-testid=\"el-menu-item\" @click=\"$emit('click', index)\"><slot /></button>",
  },
  ElButton: clickable,
  ElEmpty: passthrough,
  ElTabsPane: passthrough,
};

config.global.components = {
  ...(config.global.components || {}),
};

const messageMock = Object.assign(vi.fn(), {
  success: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
});

const messageBoxMock = {
  confirm: vi.fn(() => Promise.resolve()),
};

vi.mock("element-plus", () => ({
  ElMessage: messageMock,
  ElMessageBox: messageBoxMock,
}));
