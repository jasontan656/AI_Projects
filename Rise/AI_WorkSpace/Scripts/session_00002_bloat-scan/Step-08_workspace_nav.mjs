#!/usr/bin/env node
import { argv, exit } from "node:process";
import { performance } from "node:perf_hooks";

const arg = argv.find((item) => item.startsWith("--tabs="));
const tabs = arg ? arg.replace("--tabs=", "").split(",").map((tab) => tab.trim()).filter(Boolean)
  : ["nodes", "prompts", "workflow"];

if (!tabs.length) {
  console.error("No tabs provided. Use --tabs=nodes,prompts,...");
  exit(1);
}

const baseUrl = "http://localhost:5173/workspace";

const run = async () => {
  for (const tab of tabs) {
    const url = `${baseUrl}/${tab}`;
    const start = performance.now();
    try {
      const response = await fetch(url, { redirect: "manual" });
      const duration = (performance.now() - start).toFixed(1);
      console.log(`[workspace-nav] GET ${url} -> ${response.status} (${duration}ms)`);
    } catch (error) {
      console.error(`[workspace-nav] GET ${url} failed:`, error.message);
    }
  }

  console.log("\nNext steps (Chrome MCP manual run):");
  console.log("- mcp__chrome-devtools__navigate_page url=http://localhost:5173/workspace/nodes");
  console.log("- mcp__chrome-devtools__take_snapshot for nodes/prompts/workflow");
  console.log("- mcp__chrome-devtools__list_network_requests to confirm SSE stream remains open");
};

run();
