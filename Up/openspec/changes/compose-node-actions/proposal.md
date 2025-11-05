# Proposal: Compose Node Actions

## Background
- 节点编辑仍依赖 systemPrompt 文本域，缺乏可视化脚本化能力。
- 提示词模板与节点表单之间没有复用机制，导致内容重复与难以治理。
- 工作流节点需要显式的动作序列（提示词拼接、工具调用、输出）以对齐后端执行模型。

## Why
- 统一提示词引用，减少重复维护成本。
- 让运营人员可视化审查节点脚本，方便调试与治理。
- 为后端引擎提供结构化 ctions 契约，支持未来扩展更多动作类型。

## Problem Statement
- 自由文本的 systemPrompt 难以控制内容来源，也无法限制动作类型。
- 当关闭大模型访问时仍可编辑提示词，违反业务规则。
- 缺少标准化的动作排序/设置交互，行动配置信息分散。

## Goals
- 通过 ctions[] 列表替代 systemPrompt，结构化存储动作类型与配置。
- 引入“上移/下移”按钮与右键快捷菜单，既能维持顺序也能跳转动作设置。
- 当 llowLLM 关闭时自动禁用提示词动作并阻止保存。
- 保持 config 字段与契约一致（	emplateId、legacyText、inputMapping、disabled），并提供只读模板预览。

## Non-Goals
- 不实现后端动作执行引擎，仅定义前端契约与 UI 行为。
- 不覆盖提示词模板的版本管理或高级搜索。

## Proposed Changes
1. **Store & Contract**：扩展 pipelineDraft store 及服务层，在保存/加载时完全依赖 ctions[] 并兼容旧数据迁移。
2. **UI 编排**：动作列表提供添加、删除、上/下移动按钮，以及右键快捷菜单跳转动作设置；prompt_append 动作复用模板列表并展示只读预览。
3. **LLM Gating**：监听 llowLLM 状态，禁用或移除提示词动作，并在尝试保存时给出错误提示。
4. **契约同步**：更新 docs/contracts/pipeline-node-draft.json 示例，限制 config 字段至允许键，并记录 disabled 标记。
5. **验证**：补充测试覆盖动作排序、LLM gating、模板选择/预览，以及兼容旧 systemPrompt 的迁移流程。

## Risks & Open Questions
- 多模板拼接是否需要在单个动作内定义顺序？暂时假设按选择顺序保存。
- 右键菜单是否需要更多操作（复制、禁用等）？待真实用户反馈扩展。
