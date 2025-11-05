# Project Context

## Purpose
Up is an internal workflow-ops GUI built with Vue 3 + Pinia + Element Plus. It lets the ops/engineering team configure backend workflow nodes (LLM calls, functions, tools), reuse prompt templates, orchestrate execution order, and debug everything without touching code. The frontend acts as the live contract for the FastAPI orchestrator: we define nodes, actions, and data contracts, while the backend executes according to these specs.

## High-Level Goals
1. **Workflow node scripting** – describe each node via ordered actions (prompt append, tool invoke, emit output, …) and support future branching/conditions.
2. **Prompt template reuse** – maintain templates centrally, allow quick selection/preview in node actions, and avoid copy-paste text.
3. **Variable visibility** – surface Redis/kv variables so operators can inspect context injection and data flow.
4. **Real-time debugging** – stream execution logs, inputs/outputs, and token metrics via WebSocket/SSE for fast troubleshooting.
5. **Contract-first collaboration** – every change to nodes/templates/workflows is captured in JSON schema/examples so the backend can implement against a stable contract.

## Functional Modules
| Module | Objectives | Suggested implementation |
| ------ | ---------- | ----------------------- |
| **Node management** | Create/delete/reorder nodes; edit node type, actions, IO variables | Element Plus table/form + Pinia store; Codemirror snippet preview |
| **Prompt template hub** | Edit Markdown templates with placeholders; show version/updated info | Codemirror 6 (Markdown) + Pinia; future: template diff view |
| **Variable panel** | Browse Redis/runtime variables; search and copy values | Element Plus tree/table + `/vars` API |
| **Workflow orchestration** | Arrange execution order, visualize graph, persist workflow JSON | VueFlow + custom nodes/edges + Pinia persistence |
| **Real-time logs** | Stream node-level logs, errors, token usage | WebSocket/SSE + Element Plus timeline/log viewer |
| **Configuration export** | Save nodes/templates/workflow; emit contract snapshots | Axios REST + local fallback cache |

### Layout Recommendation
```
┌────────────┬────────────────────────────────────┐
│ Side nav   │ Main panel (tabs: Nodes / Prompts / │
│ (Nodes,    │ Workflow / Variables / Logs / Settings) │
│ Prompts…)  │                                        │
└────────────┴────────────────────────────────────┘
```
- Top bar: workflow selector, save/publish buttons, contract preview toggle.
- Right drawer (optional): live log stream or JSON diff viewer.

## Tech Stack

**VueFlow-law:** use VueFlow for visual workflow editing—nodes, edges, drag, zoom, custom node types, events, and JSON state.

| Layer | Technology | Notes |
| ----- | ---------- | ----- |
| Framework | Vue 3 (Composition API) + Vite | Fast dev server, modular components |
| State | Pinia | Stores for nodes, prompts, workflow, variables, logs |
| UI kit | Element Plus | Tables, forms, drawers, dialogs, notifications |
| Workflow canvas | VueFlow | Drag/zoom/edge editing, custom node types, JSON state |
| Code editor | Codemirror 6 + themes (`@codemirror/theme-one-dark`, `@codemirror/lang-*`) | For prompt editing, action preview, JSON schema |
| Utilities | VueUse, uuid/nanoid, zod/valibot (optional validation) | Helpful composables and ID helpers |
| Networking | Axios | REST wrapper, interceptors for auth/logging |
| Real-time | WebSocket or SSE | Live logs; fallback to polling if backend not ready |
| Testing | Vitest + Vue Testing Library + Chrome DevTools AI/Playwright | Unit + E2E coverage |

## Architecture Overview
```
[Vue3 GUI]
  ├─ Node table & action editor (Element Plus + Pinia + Codemirror)
  ├─ Prompt template hub (Pinia + Codemirror)
  ├─ Workflow canvas (VueFlow)
  ├─ Variable panel (Redis browser)
  └─ Real-time logs (WebSocket/SSE viewer)
        ↓ REST / WS
[FastAPI Orchestrator]
  ├─ /nodes /workflow /prompts /vars /logs APIs
  └─ Graph runner (asyncio)
        ├─ LLM/tool adapters
        ├─ Redis context
        └─ Telemetry + monitoring
```
- Frontend emits JSON contract snapshots in `docs/contracts/`.
- Backend reads `actions` arrays to execute node scripts.

## Collaboration & Contract
- **Contract first** – update Pinia store schemas & `docs/contracts/*.json` before backend work begins.
- **Frontend demo = living doc** – DevTools AI recordings/screenshots accompany each change.
- **Version sync** – keep contract files in lockstep with implementation; any mutation requires documentation.
- **Testing policy**:
  - DevTools AI: regress node creation, template selection, workflow save, LLM gating, log streaming.
  - Unit tests: cover serialization/normalization of actions and prompt selection flows.
  - If VueFlow interactions change, supply E2E scripts or manual test evidence.
- **Backend alignment**:
  - Provide `/nodes`, `/workflow`, `/prompts`, `/vars`, `/logs` endpoints respecting contract fields.
  - Supply WebSocket/SSE logs; specify fallback if unavailable.
- **Integration-law:** check community fixes and common bugs through Context7 before implementing new libraries.
  - Known issue, best practise.
- **Frontend-law:** always use ChromeDevTools MCP to inspect DOM, CSS, and layout before modifying or debugging frontend code.
  - Box arrangement. visual view.
## Terminology
| Term | Definition |
| ---- | ---------- |
| Node | Executable unit (LLM/function/tool) in the workflow |
| Action | Script step inside a node (prompt_append, tool_invoke, …) |
| Prompt template | Reusable Markdown prompt with placeholders |
| Variable injection | Inserting Redis/runtime variables into prompts/inputs |
| Orchestrator | FastAPI service that executes the workflow graph |
| Ops Config UI | Internal console for configuring pipelines |

## Roadmap Notes
1. **MVP** – action list editor, template picker with preview, basic log stream.
2. **Phase II** – VueFlow canvas with drag/zoom, template diff/history, variable hot reload.
3. **Phase III** – conditional/parallel actions, full graph visualization, offline tool adapters.

## External Dependencies
- FastAPI orchestrator APIs (`/nodes`, `/workflow`, `/prompts`, `/vars`, `/logs`)
- Redis (context + variable cache)
- LLM providers (OpenAI/Anthropic via backend)
- WebSocket/SSE service for live logs
- Chrome DevTools AI / Playwright for regression testing

## Constraints
- Stick to JavaScript until contracts stabilize (no TS yet).
- Optimize for latest Chrome; other modern browsers as best effort.
- Every new module must ship with minimal UI placeholders.
- Keep contract snapshots current; run contract validation before merging.
- DevTools AI regression is mandatory for user-facing flows.
