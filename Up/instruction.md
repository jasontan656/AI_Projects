• 前端最新能力对应的后端需求

  1. 节点管理 API 扩展
      - GET /api/pipeline-nodes?page=1&pageSize=50
        返回数组或 { items: [...] }，元素需包含 id, name, allowLLM, systemPrompt, createdAt,
        updatedAt（若有）以及可选 latestSnapshot。
      - PUT /api/pipeline-nodes/:id
        接受 JSON：{ name, allowLLM, systemPrompt, status?, pipelineId?, strategy? }，回传更新后的
        节点。
      - DELETE /api/pipeline-nodes/:id
        无需响应体或返回 { success: true }。前端会在确认后调用；若节点不存在需返回 404/适当错误
        描述。
  2. 提示词管理 API 扩展
      - GET /api/prompts?page=1&pageSize=50
        与节点相同格式，至少包含 id, name, markdown, createdAt, updatedAt（可选）。
      - PUT /api/prompts/:id
        接受 { name, markdown } 并回传更新后的提示词。
      - DELETE /api/prompts/:id
        删除指定提示词并返回成功标记或 204。
  3. 一致性／错误处理
      - DELETE/PUT 操作失败时输出结构化错误，例如 { detail: "原因" }，前端统一展示。
      - 删除成功后不再返回旧数据，以免前端误写回缓存。
      - 所有时间字段建议 ISO8601（UTC）格式，后续若提供版本号、作者等扩展字段请保持可选