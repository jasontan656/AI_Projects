# Variables 变量面板

## 1. 目标
- 提供运行时变量浏览与复制功能，辅助 Ops 调试。
- 作为未来连接 Redis / API 的占位实现。

## 2. 组件：VariablesPanel（src/components/VariablesPanel.vue）
- Element Plus 组件：`el-input`（搜索）、`el-scrollbar`（列表）、`el-empty`（空状态）、`el-button`（复制）。
- 依赖 `@vueuse/core` 的 `useStorage` 持久化默认变量。

## 3. 数据结构
```js
const DEFAULT_VARIABLES = [
  { key: "session.userId", value: "ops_admin_001" },
  ...
];
```
- `persisted` 为响应式数组，可后续替换为 API 返回。
- `filteredVariables` 根据搜索词过滤 key/value。

## 4. 交互
- 搜索框支持清除，输入后实时过滤。
- 复制按钮调用 `navigator.clipboard.writeText`，成功/失败通过 `ElMessage` 提示。
- 无匹配结果时显示空状态说明。

## 5. 扩展规划
1. 接入真实 API（如 `/vars`），支持分页与分类（scope）。
2. 为复杂值提供 JSON 折叠视图，可引入 `vue-json-pretty`。
3. 增加标签/过滤器，例如仅查看 session / context / cache。
4. 支持导出当前变量快照。
5. 补充鉴权与敏感字段遮罩逻辑。
