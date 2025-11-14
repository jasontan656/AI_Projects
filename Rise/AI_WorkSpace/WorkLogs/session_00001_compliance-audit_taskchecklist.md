# session_00001_compliance-audit Task Checklist
- [x] Step-01 上行依赖守护脚本（`Step-01_import_guard.py` + allowlist/report/log）
- [x] Step-02 Foundational contracts 与 worker 注入（contracts/* + `interface_entry/runtime/workflow_executor.py` + `Step-02_pytest.log`）
- [x] Step-03 Telegram 表征测试基线（tests/business_service/conversation + fixtures/snapshots + `Step-03_golden_fixture_builder.py`，证据：`Step-03_fixture_verify.log`、`Step-03_pytest.log`）
- [x] Step-04 Runtime Gateway 心跳与队列护栏（runtime_dispatch/ChannelHealthStore + `test_runtime_gateway.py`，证据：`Step-04_pytest.log`）
- [x] Step-05 Coverage 状态服务与 `/tests/run` API（coverage_status.py + workflow routes + seed 脚本，证据：`Step-05_pytest.log`）
- [x] Step-06 Up 覆盖门禁 UI/Pinia（channel-form 子组件 + channelPolicy store + Vitest，证据：`Step-06_vitest.log`）
- [x] Step-07 Webhook Secret/TLS 守护（`PublicEndpointSecurityProbe` + `WebhookCredentialRotatedEvent` + chromedevtoolmcp 证据；测试日志 `Step-07_observability_pytest.log`、`Step-07_channel_bootstrap_pytest.log`，浏览器采样 `Step-07_docs_snapshot.png` / `Step-07_up_snapshot.png`）
- [x] Step-08 Up Secret/TLS 表单与提示（ChannelFieldsSecurity + ChannelTestPanel）【证据：`AI_WorkSpace/Scripts/session_00001_compliance-audit/Step-08_vitest.log`、`Step-08_channel_security.png`、`Step-08_channel_console.log`、`Step-08_channel_network.log`】
- [x] Step-09 Webhook vs Polling 互斥（ChannelMode policy + conflict tests + matrix JSON）——代码已加入 ChannelMode/WorkflowChannelPolicy.mode、DTO usePolling 校验，`PYTHONPATH=src pytest tests/business_service/channel/test_channel_modes.py -vv`（日志：AI_WorkSpace/Scripts/session_00001_compliance-audit/Step-09_pytest.log；矩阵：Step-09_conflict_matrix.json）
- [x] Step-10 Up Polling 模式提示与 store 逻辑（channelPolicy/usePolling + WorkflowChannelForm）——已扩展 schema/store/client、ChannelCoverageGate 与 ChannelTestPanel Polling 提示，命令：`VITEST_WORKSPACE_ROOT=tests VITEST_SETUP_PATH=tests/setup/vitest.setup.js pnpm vitest run tests/unit/channelPolicyStore.spec.ts tests/unit/ChannelCoverageGate.spec.ts tests/unit/ChannelTestPanel.spec.ts`；证据：Step-10_vitest.log、Step-10_ui_snapshot.json、Step-10_console.log、Step-10_network.log。
- [x] Step-11 覆盖 Telemetry/SSE/日志工单（`CoverageTestEventRecorder` + `/api/workflows/{id}/tests/stream` + ChannelTestPanel SSE，证据：Step-11_pytest.log、Step-11_vitest.log、Step-11_up_snapshot.png、Step-11_tests_stream.png、Step-11_tail_telemetry.ps1）
- [x] Step-12 护栏与 CI 验证（`CI/scripts/check_characterization.sh` + `Step-12_ci_guard.sh`、Step-12_import_guard.log/characterization_pytest.log/coverage_pytest.log/radon.log/madge.log/schemathesis.log/vitest.log，记录 bash 缺失导致单步执行）


