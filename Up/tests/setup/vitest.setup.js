import { vi } from "vitest";
import { config } from "@vue/test-utils";

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
