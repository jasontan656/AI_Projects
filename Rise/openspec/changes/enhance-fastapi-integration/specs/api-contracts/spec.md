## ADDED Requirements

### Requirement: Standardised API Response Envelope
所有 FastAPI 路由 MUST 返回统一的响应模型 `ApiResponse[T]`，包含 `data`, `meta`, `errors` 字段；错误场景返回 `ApiError` 枚举结构并由全局异常处理器生成。

#### Scenario: Prompt not found returns typed error
- **GIVEN** 请求删除不存在的 prompt
- **WHEN** handler 引发 `KeyError`
- **THEN** 全局异常处理器返回 `{"data": null, "meta": {...}, "errors": [{"code": "PROMPT_NOT_FOUND", "message": "..."}]}`，HTTP 状态为 404。

### Requirement: Actor Context Dependency
接口层 MUST 通过统一的 `Depends(get_actor_context)` 解析身份、角色与租户信息；若缺少必要凭证，路由需返回 401/403，并阻止后续业务逻辑执行。

#### Scenario: Missing actor header rejected
- **GIVEN** 客户端未传递任何身份 header/JWT
- **WHEN** 调用 `POST /api/pipeline-nodes`
- **THEN** `get_actor_context` 抛出授权异常
- **AND** API 返回 401 `UNAUTHENTICATED`，不触发任何数据库写入。
