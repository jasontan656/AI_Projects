# Tasks

1. 复查 `PipelineWorkspace` 现有节点视图状态与事件监听，实现方案走查。
2. 重构 `PipelineWorkspace`，新增 `menu` 视图状态，移除浮层定位逻辑，将 NodeSubMenu 渲染到主区域；更新返回按钮逻辑。
3. 调整 `NodeSubMenu` 布局与样式，使其在主区域呈现卡片/面板样式并支持键鼠操作。
4. 补充/校正相关样式与状态流（包括 Pinia 交互），确保 create/manage 流程保持可用且保存后刷新列表。
5. 回归测试节点创建、切换视图、节点删除等流程；执行 `npm run build` 或对应检查。
6. 更新相关文档（如 `docs/ProjectDev` 节点交互说明）描述新的菜单位置与交互。
