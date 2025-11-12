# 函数索引

_生成时间：2025-11-12T18:16:42+00:00_

## rise-project-utility（rise）

### Project Utility Layer

- `src/project_utility/logging.py` · `def initialize_log_workspace(*, log_root: Optional[Path]=None) -> Path` · 63 行
  - 说明：Prepare `var/logs` for a fresh runtime session.
  - 片段：def initialize_log_workspace(*, log_root: Optional[Path] = None) -> Path:     """     Prepare `var/logs` for a fresh runtime session.
- `src/project_utility/logging.py` · `def finalize_log_workspace(*, reason: str='shutdown') -> None` · 45 行
  - 说明：Flush logging handlers and optionally clean runtime logs.
  - 片段：def finalize_log_workspace(*, reason: str = "shutdown") -> None:     """Flush logging handlers and optionally clean runtime logs.""" 
- `src/project_utility/logging.py` · `def configure_logging(*, log_root: Optional[Path]=None, extra_loggers: Optional[Dict[str, Dict[str, Any]]]=None) -> Dict[str, logging.Logger]` · 42 行
  - 说明：Configure structured logging for Rise services.
  - 片段：def configure_logging(     *,     log_root: Optional[Path] = None,
- `src/project_utility/db/redis.py` · `async def append_chat_summary(chat_id: str | int, entry: Mapping[str, Any], *, max_entries: int=20, ttl_seconds: Optional[int]=None) -> None` · 17 行 · async
  - 说明：Append a chat summary entry while trimming to the configured max length.
  - 片段：async def append_chat_summary(     chat_id: str | int,     entry: Mapping[str, Any],
- `src/project_utility/tracing.py` · `def trace_span(name: str, **attributes) -> TraceSpan` · 10 行
  - 说明：Create an asynchronous trace span context manager.
  - 片段：def trace_span(name: str, **attributes: Any) -> TraceSpan:     """     Create an asynchronous trace span context manager.
- `src/project_utility/config/paths.py` · `def get_repo_root() -> Path` · 9 行
  - 说明：Return the absolute path to the Rise repository root.
  - 片段：def get_repo_root() -> Path:     """Return the absolute path to the Rise repository root.""" 

### One-off Utility Layer

- `src/one_off/sources/service_crawler/fetch_forms.py` · `def llm_extract_attachments(client: Optional[OpenAI], model: str, service_name: str, service_url: str, article_text: str, anchor_candidates: List[Attachment]) -> List[Attachment]` · 105 行
  - 说明：（无 docstring，参考片段）
  - 片段：def llm_extract_attachments(     client: Optional[OpenAI],     model: str,
- `src/one_off/sources/service_crawler/rename_attachments.py` · `def request_filename_from_llm(client: OpenAI, model: str, attachment: Attachment, content: str, image_b64: Optional[str]=None, prompt_template: str='') -> str` · 69 行
  - 说明：（无 docstring，参考片段）
  - 片段：def request_filename_from_llm(     client: OpenAI,     model: str,
- `src/one_off/sources/service_crawler/rename_attachments.py` · `def main(argv: List[str]) -> int` · 64 行
  - 说明：（无 docstring，参考片段）
  - 片段：def main(argv: List[str]) -> int:     parser = argparse.ArgumentParser(description="调用 LLM 为 BI 附件生成语义化文件名。")     parser.add_argument(
- `src/one_off/sources/service_crawler/fetch_visas.py` · `def main()` · 54 行
  - 说明：（无 docstring，参考片段）
  - 片段：def main():     setup_environment()     session = requests.Session()
- `src/one_off/sources/service_crawler/rename_attachments.py` · `def process_attachment(console: Console, client: OpenAI, model: str, attachment: Attachment, dry_run: bool=False) -> Optional[Path]` · 53 行
  - 说明：（无 docstring，参考片段）
  - 片段：def process_attachment(     console: Console,     client: OpenAI,
- `src/one_off/sources/service_crawler/rewrite_md.py` · `def process_files(tasks: List[Tuple[Path, Path | None, Path]]) -> None` · 48 行
  - 说明：（无 docstring，参考片段）
  - 片段：def process_files(tasks: List[Tuple[Path, Path | None, Path]]) -> None:     load_env()     template_text, price_text = read_required_files()

### Foundational Service Layer

- `src/foundational_service/bootstrap/aiogram.py` · `def bootstrap_aiogram(*, repo_root: Path | str, redis_url: Optional[str]=None, runtime_policy_path: Optional[Path | str]=None, attach_handlers: bool=True) -> Dict[str, Any]` · 110 行
  - 说明：Initialise aiogram dispatcher, runtime policy, and telemetry context.
  - 片段：def bootstrap_aiogram(     *,     repo_root: Path | str,
- `src/foundational_service/contracts/telegram.py` · `def behavior_telegram_inbound(update: Mapping[str, Any], policy: Mapping[str, Any]) -> Dict[str, Any]` · 87 行
  - 说明：（无 docstring，参考片段）
  - 片段：def behavior_telegram_inbound(     update: Mapping[str, Any],     policy: Mapping[str, Any],
- `src/foundational_service/contracts/telegram.py` · `def build_core_schema(update: Dict[str, Any], channel: str) -> Dict[str, Any]` · 77 行
  - 说明：（无 docstring，参考片段）
  - 片段：def build_core_schema(update: Dict[str, Any], channel: str) -> Dict[str, Any]:     if channel != "telegram":         raise ChannelNotSupportedError(channel)
- `src/foundational_service/bootstrap/webhook.py` · `async def behavior_webhook_startup(bot: Any, webhook_url: str, secret: str, *, retries: int=2, drop_pending_updates: bool=False, max_connections: Optional[int]=None) -> Dict[str, Any]` · 66 行 · async
  - 说明：Register Telegram webhook with retry telemetry.
  - 片段：async def behavior_webhook_startup(     bot: Any,     webhook_url: str,
- `src/foundational_service/telemetry/config.py` · `def load_telemetry_config() -> Dict[str, Any]` · 42 行
  - 说明：Load telemetry configuration, merging defaults with YAML overrides.
  - 片段：def load_telemetry_config() -> Dict[str, Any]:     """Load telemetry configuration, merging defaults with YAML overrides.""" 
- `src/foundational_service/persist/controllers.py` · `def build_task_admin_router(runtime_provider: Callable[[], Optional[TaskRuntime]]) -> APIRouter` · 41 行
  - 说明：（无 docstring，参考片段）
  - 片段：def build_task_admin_router(runtime_provider: Callable[[], Optional[TaskRuntime]]) -> APIRouter:     router = APIRouter(prefix="/internal/tasks", tags=["internal-tasks"]) 

### Interface / Entry Layer

- `src/interface_entry/bootstrap/application_builder.py` · `def configure_application(app: FastAPI) -> FastAPI` · 528 行
  - 说明：（无 docstring，参考片段）
  - 片段：def configure_application(app: FastAPI) -> FastAPI:     initialize_log_workspace()     configure_logging()
- `src/interface_entry/telegram/routes.py` · `def register_routes(app: FastAPI, dispatcher: Dispatcher, webhook_path: str, runtime_policy: dict[str, Any], webhook_secret: str) -> None` · 261 行
  - 说明：（无 docstring，参考片段）
  - 片段：def register_routes(     app: FastAPI,     dispatcher: Dispatcher,
- `src/interface_entry/telegram/handlers.py` · `async def handle_message(message: Message, bot: Bot) -> None` · 205 行 · async
  - 说明：（无 docstring，参考片段）
  - 片段：async def handle_message(message: Message, bot: Bot) -> None:     start = perf_counter()     request_id = ContextBridge.request_id()
- `src/interface_entry/telegram/runtime.py` · `def bootstrap_aiogram_service(api_token: str, webhook_url: str, redis_url: str | None=None, fastapi_app: FastAPI | None=None) -> BootstrapState` · 105 行
  - 说明：（无 docstring，参考片段）
  - 片段：def bootstrap_aiogram_service(     api_token: str,     webhook_url: str,
- `src/interface_entry/bootstrap/runtime_lifespan.py` · `def configure_runtime_lifespan(app: FastAPI, *, capability_registry: CapabilityRegistry, runtime_supervisor: RuntimeSupervisor, application_lifespan: Callable[[], Any], log, extra_contexts: Optional[Sequence[AsyncLifespanContextFactory]]=None) -> None` · 83 行
  - 说明：Attach the unified async lifespan that drives capability probes and runtime shutdown.
  - 片段：def configure_runtime_lifespan(     app: FastAPI,     *,
- `src/interface_entry/bootstrap/application_builder.py` · `def perform_clean_startup() -> None` · 69 行
  - 说明：（无 docstring，参考片段）
  - 片段：def perform_clean_startup() -> None:     release_logging_handlers()     log_root = initialize_log_workspace()

### Business Service Layer

- `src/business_service/conversation/config.py` · `def resolve_entry_config(policy: Mapping[str, Any], *, binding_policy: Optional[WorkflowChannelPolicy]=None, defaults: Optional[TelegramEntryConfig]=None) -> TelegramEntryConfig` · 55 行
  - 说明：Merge policy entrypoints + binding overrides into a resolved config.
  - 片段：def resolve_entry_config(     policy: Mapping[str, Any],     *,
- `src/business_service/conversation/config.py` · `def load_default_entry_config() -> TelegramEntryConfig` · 16 行
  - 说明：Load defaults from environment to allow operator override.
  - 片段：def load_default_entry_config() -> TelegramEntryConfig:     """Load defaults from environment to allow operator override.""" 
- `src/business_service/conversation/runtime_gateway.py` · `def set_task_queue_accessors(*, submitter_factory: SubmitterFactory, runtime_factory: RuntimeFactory) -> None` · 10 行
  - 说明：Register factories used by the default runtime gateway.
  - 片段：def set_task_queue_accessors(     *,     submitter_factory: SubmitterFactory,
- `src/business_service/conversation/health.py` · `def build_default_health_reporter(ttl_seconds: int=120) -> ChannelHealthReporter` · 6 行
  - 说明：（无 docstring，参考片段）
  - 片段：def build_default_health_reporter(ttl_seconds: int = 120) -> ChannelHealthReporter:     return ChannelHealthReporter(         store=ChannelBindingHealthStore(),
- `src/business_service/conversation/service.py` · `def set_channel_binding_health_store(store: ChannelBindingHealthStore) -> None` · 5 行
  - 说明：Compatibility shim to keep existing bootstrap wiring intact.
  - 片段：def set_channel_binding_health_store(store: ChannelBindingHealthStore) -> None:     """Compatibility shim to keep existing bootstrap wiring intact.""" 
- `src/business_service/conversation/service.py` · `def set_channel_binding_provider(provider: ChannelBindingProvider) -> None` · 5 行
  - 说明：Register the global channel binding provider used by conversation flows.
  - 片段：def set_channel_binding_provider(provider: ChannelBindingProvider) -> None:     """Register the global channel binding provider used by conversation flows.""" 

## up（up）

### Foundational Service Layer

- `src/services/logService.js` · `subscribeWorkflowLogs(workflowId,
  { onMessage, onError, heartbeatMs } = {})` · 15 行
  - 说明：（无 docstring，参考片段）
  - 片段：export function subscribeWorkflowLogs(   workflowId,   { onMessage, onError, heartbeatMs } = {}
- `src/services/pipelineService.js` · `deletePipelineNode(nodeId)` · 13 行
  - 说明：（无 docstring，参考片段）
  - 片段：export async function deletePipelineNode(nodeId) {   if (!nodeId) {     throw new Error("缺少节点 ID");
- `src/services/promptService.js` · `updatePrompt(promptId, payload = {})` · 13 行
  - 说明：（无 docstring，参考片段）
  - 片段：export async function updatePrompt(promptId, payload = {}) {   if (!promptId) {     throw new Error("缺少提示词 ID");
- `src/services/workflowService.js` · `publishWorkflow(workflowId, payload = {})` · 13 行
  - 说明：（无 docstring，参考片段）
  - 片段：export async function publishWorkflow(workflowId, payload = {}) {   if (!workflowId) {     throw new Error("缺少 workflowId");
- `src/services/promptService.js` · `deletePrompt(promptId)` · 12 行
  - 说明：（无 docstring，参考片段）
  - 片段：export async function deletePrompt(promptId) {   if (!promptId) {     throw new Error("缺少提示词 ID");
- `src/services/workflowService.js` · `listWorkflows(params = {})` · 12 行
  - 说明：（无 docstring，参考片段）
  - 片段：export async function listWorkflows(params = {}) {   const query = new URLSearchParams();   if (params.search) {

### Unmapped

- `src/schemas/workflowDraft.js` · `createWorkflowDraft(overrides = {})` · 13 行
  - 说明：（无 docstring，参考片段）
  - 片段：export function createWorkflowDraft(overrides = {}) {   return {     ...WORKFLOW_DEFAULT,
- `src/schemas/channelPolicy.js` · `createChannelPolicy(overrides = {})` · 12 行
  - 说明：（无 docstring，参考片段）
  - 片段：export function createChannelPolicy(overrides = {}) {   const merged = {     ...CHANNEL_POLICY_DEFAULT,
- `src/schemas/channelPolicy.js` · `normalizeChannelPolicyResponse(response)` · 10 行
  - 说明：（无 docstring，参考片段）
  - 片段：export function normalizeChannelPolicyResponse(response) {   if (!response) {     return createChannelPolicy();
- `src/schemas/workflowDraft.js` · `buildWorkflowPayload(payload = {})` · 10 行
  - 说明：（无 docstring，参考片段）
  - 片段：export function buildWorkflowPayload(payload = {}) {   const nodeSequence = normalizeNodeSequence(payload.nodeSequence);   if (!nodeSequence.length) {
- `src/schemas/workflowDraft.js` · `normalizeWorkflowEntity(entity)` · 10 行
  - 说明：（无 docstring，参考片段）
  - 片段：export function normalizeWorkflowEntity(entity) {   if (!entity) {     return createWorkflowDraft();
- `src/schemas/channelPolicy.js` · `getTestCooldownUntil(state, now = Date.now()` · 9 行
  - 说明：（无 docstring，参考片段）
  - 片段：export function getTestCooldownUntil(state, now = Date.now()) {   pruneTestAttempts(state, now);   if (state.attempts.length < CHANNEL_TEST_RULE.maxAttempts) {
