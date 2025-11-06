# Workflow 画布模块

## 1. 当前状态
- 组件：`WorkflowCanvas`（src/components/WorkflowCanvas.vue）。
- 依赖：`@vue-flow/core`。
- 功能：渲染静态示例节点/边，展示画布预留区域、说明文字。

## 2. 结构
```
section.workflow-canvas
 ├─ header → 标题 + 说明
 ├─ div.workflow-canvas__body → VueFlow 容器
 └─ footer → 备注信息
```

- VueFlow 通过 `fit-view` 初始缩放。
- 示例节点：start (input)、llm (default)、tool (default)、end (output)。
- 示例边：含动画、基本连线，展示并行路径。

## 3. 目标功能（规划）
1. 与 `pipelineDraft.nodes` 同步，动态生成节点/连线。
2. 支持拖拽调整顺序、双击编辑节点属性。
3. 右键菜单：跳转到节点表单、复制、删除。
4. 显示节点运行状态（成功/失败/耗时）。
5. 导出 JSON/图片，作为调试或合同资料。

## 4. 技术要点
- VueFlow 节点数据结构：`{ id,label,type,position,data }`。
- 连接元素需要保证 id 唯一，可复用 `uuid`。
- 若要实现自动布局，可引入 dagre 等算法。
- 与 Nodes 表单交互时需保持状态源一致（Pinia）。

## 5. 后续建议
- 在画布上集成“新增节点”拖拽面板，与表单同步。
- 引入 minimap、controls、背景网格等 VueFlow 插件。
- 为节点提供状态徽标（Element Plus Tag）。
- 支持复合结构（条件分支、并行段），可在 `actions` schema 中扩展。
