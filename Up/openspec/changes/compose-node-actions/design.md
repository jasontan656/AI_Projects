# Design Notes

## 状态建模
- pipelineDraft store 扩展字段：ctions: ActionDraft[]。
- ActionDraft 结构：
  `	s
  interface ActionDraft {
    id: string;
    type: "prompt_append" | "tool_invoke" | "emit_output" | string;
    config: {
      templateId?: string | null;
      legacyText?: string | null;
      inputMapping?: Record<string, unknown> | null;
      disabled?: boolean;
    };
    order: number;
  }
  `
- 保存时提交 ctions；加载旧节点若仅有 systemPrompt，转化为 prompt_append 并填充 config.legacyText。

## UI 结构
- 动作列表组件负责：
  - 按 order 排序渲染条目；提供“上移”“下移”“删除”按钮。
  - 响应右键事件，展示快捷菜单（查看设置、跳转到 Prompts、禁用/启用）。
  - 对 prompt_append 类型弹出模板选择抽屉，数据源来自 promptDraftStore.prompts，预览区只读。
- llowLLM 监听：
  - 关闭时将相关动作标记 disabled = true，顶部展示阻止保存的警告；保存前校验不含启用的 prompt_append。

## 数据流
1. 加载时优先读取后端 ctions，缺失时根据 systemPrompt 生成迁移动作。
2. 保存前归并 order 为 0..n-1，剔除禁用的 prompt_append。
3. 提交后更新 docs/contracts/pipeline-node-draft.json，保持 	emplateId 与 legacyText 字段一致。

## 风险缓解
- config 采用显式键，使用 zod/valibot 校验；额外字段拒绝透传。
- 通过单元测试覆盖排序、快捷菜单触发、LLM gating 流程。
- 预留 future hooks 以支持并行或条件动作类型。
