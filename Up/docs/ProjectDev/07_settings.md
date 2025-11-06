# Settings 模块展望

## 1. 当前状态
- `PipelineWorkspace` 中 `activeNav === "settings"` 时渲染 `workspace-pane--settings`。
- 仅展示 Element Plus `el-empty` 与占位说明，未接入任何配置项。

## 2. 未来可规划的能力
1. **环境令牌管理**：配置后端访问密钥、第三方服务凭证。
2. **调试选项**：切换 mock 接口、启用 verbose 日志、设置默认 pipeline。
3. **导出策略**：一键导出节点/模板契约与测试脚本。
4. **通知/告警**：配置 Webhook、邮箱、机器人。
5. **权限控制**：为不同用户组分配可见模块/操作。

## 3. 设计建议
- 采用 `el-form` + 分组面板方式组织设置项。
- 可引入 Tab 或 Collapse 将配置划分为“系统”、“日志”、“集成”等类别。
- 保存前提供变更 diff 与一键恢复默认。
- 与后端接口保持幂等，确保失败时提示明确原因。
