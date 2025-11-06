# Logs 实时日志面板

## 1. 目标
- 在线监控节点执行日志，辅助运维快速定位问题。
- 支持实时流、模拟测试、自动滚动控制。

## 2. 组件：LogsPanel（src/components/LogsPanel.vue）
- 使用 Element Plus 控件：`el-switch`、`el-button`、`el-alert`、`el-scrollbar`。
- 日志消息以 `[{ id, timestamp, level, message }]` 形式保留。

## 3. 功能点
1. **连接/断开**：`toggleConnection()` 切换 `connected` 状态，插入“已建立连接/连接关闭”系统日志。
2. **模拟事件**：`simulateEvent()` 随机生成示例日志（INFO/WARN/ERROR），用于开发阶段演示。
3. **自动滚动**：当 `autoScroll=true` 时新日志会滚动到底部。
4. **日志容量**：保留最近 200 条，防止列表无限增长。
5. **UI 反馈**：未连接时显示 `el-alert` 提示，连接后展示日志列表。

## 4. 后续版本规划
- 接入真实 WebSocket/SSE：
  - `EventSource` 或 `WebSocket`，在 onmessage 中 push 数据。
  - 断线重连策略、心跳检测。
- 日志增强：
  - 过滤器（按 level / 节点 / 时间段）。
  - 搜索与高亮。
  - 导出日志到文件。
- 可视化：为不同级别设置颜色标签或图标。
- 性能优化：大量日志时可使用虚拟列表（如 vue-virtual-scroller）。

## 5. 依赖与注意事项
- `uuid` 用于生成日志 id。
- 使用 `ElMessage` 反馈模拟事件未连接的提示。
- Clipboard/下载等扩展需考虑浏览器权限与安全策略。
