import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const linkedWorkspaceRoot = resolve(__dirname, "tests/session_20251112_1130_dev");
const remoteWorkspaceRoot = resolve(
  __dirname,
  "../Rise/AI_WorkSpace/Scripts/session_20251112_1130_dev/tests/vitest",
);
const workspaceTestRoot =
  process.env.VITEST_WORKSPACE_ROOT ||
  (fs.existsSync(linkedWorkspaceRoot) ? linkedWorkspaceRoot : remoteWorkspaceRoot);
const setupFile =
  process.env.VITEST_SETUP_PATH ||
  resolve(workspaceTestRoot, "setup/vitest.setup.js");
const testUtilsModule = resolve(
  __dirname,
  "node_modules/@vue/test-utils/dist/vue-test-utils.esm-bundler.js",
);
const elementPlusEntry = resolve(__dirname, "node_modules/element-plus/dist/index.full.mjs");
const piniaEntry = resolve(__dirname, "node_modules/pinia/dist/pinia.mjs");

export default defineConfig({
  plugins: [vue()],
  server: {
    fs: {
      allow: [__dirname, workspaceTestRoot, remoteWorkspaceRoot],
    },
  },
  resolve: {
    alias: {
      "@up": resolve(__dirname, "src"),
      "@vue/test-utils": testUtilsModule,
      "element-plus": elementPlusEntry,
      pinia: piniaEntry,
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: setupFile,
    include: [
      "tests/**/*.spec.{js,ts,tsx}",
      `${workspaceTestRoot.replace(/\\/g, "/")}/**/*.spec.{js,ts}`,
    ],
  },
});
