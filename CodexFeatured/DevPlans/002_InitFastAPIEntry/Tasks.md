# FastAPI 程序入口与日志闭环 开发任务列表

## 项目概述
- 目标：新增 `Kobe/main.py` 作为 FastAPI 程序入口，提供 `GET /health`，并在启动时使用 RichLogger 完成统一日志初始化，形成可运行的最小闭环。
- 技术栈：FastAPI、uvicorn、logging、Rich（Kobe/SharedUtility/RichLogger）
- 开发环境：Python 3.10，venv: `Kobe\\.venv`

## 技术调研总结
### 官方规范要点（已访问验证）
- FastAPI（https://fastapi.tiangolo.com/）
  - 应用实例命名为 `app`，便于 `uvicorn module:app` 启动。
  - 路由语义清晰、返回模型尽量简单稳定；健康检查常用 `GET /health`。
- uvicorn（https://www.uvicorn.org/）
  - 推荐使用 CLI：`uvicorn package.module:app --host --port`；开发模式可加 `--reload`，生产禁用。
- Rich（https://rich.readthedocs.io/en/stable/）
  - Console/Traceback 单例化或集中管理，避免重复创建；日志与回溯能美化输出。

### 社区最佳实践（来源可访问）
- GitHub/encode/uvicorn、GitHub/tiangolo/fastapi：模块路径启动、分离应用与服务器进程、健康检查路由命名统一。
- Stack Overflow fastapi 标签：建议健康检查返回固定键（如 `status: ok`）、使用环境变量控制 host/port。

## 任务依赖图（文本）
- T1 基础依赖补充 → T2 程序入口与路由 → T3 日志与回溯初始化 → T4 双启动方式验证 → T5 测试 → T6 文档与示例

## 详细任务列表

### 任务 T1：依赖补充（Kobe/Requirements.txt）
- 目标：为最小闭环补充必要依赖。
- 输入：`CodexFeatured/Common/BackendConstitution.md`；现有 `Kobe/Requirements.txt`。
- 输出：在 `Kobe/Requirements.txt` 追加 `fastapi`、`uvicorn[standard]`。
- 执行步骤：
  1. 打开 `Kobe/Requirements.txt`，追加两行依赖（遵循 UTF-8）。
  2. 说明注释：来源为最小闭环所需。
- 验收标准：
  - [ ] 两个依赖存在且拼写正确。
  - [ ] 不移除既有依赖。
- 注释要求：参照 `CodeCommentStandard.md`（在文件中用简短中文注释标明用途）。
- 预计耗时：0.2h

### 任务 T2：程序入口与应用对象
- 目标：新增 `Kobe/main.py`，创建 `FastAPI` 实例与 `GET /health` 路由。
- 输入：需求文档约束；FastAPI 官方约定。
- 输出：`Kobe/main.py` 文件；定义 `app` 变量；实现 `/health` 返回 `{\"status\":\"ok\"}`。
- 执行步骤：
  1. 在 `Kobe/` 目录新增 `main.py`。
  2. 创建 FastAPI 应用 `app = FastAPI()`。
  3. 定义 `@app.get("/health")` 返回 `{\"status\":\"ok\"}`。
- 验收标准：
  - [ ] 存在 `app` 变量，供 `uvicorn Kobe.main:app` 启动。
  - [ ] `GET /health` 返回 200 且 JSON 正确。
- 注释要求：关键处使用行动叙事式注释，简述职责与输入输出约束。
- 预计耗时：0.3h

### 任务 T3：统一日志与回溯初始化
- 目标：在程序入口初始化 RichLogger，确保全局一次性生效；安装美化回溯。
- 输入：`Kobe/SharedUtility/RichLogger` 包 API；BackendConstitution 约束。
- 输出：在 `Kobe/main.py` 中调用 `init_logging(level=\"INFO\")` 与 `install_traceback()`。
- 执行步骤：
  1. 在模块导入或 `if __name__ == \"__main__\":` 路径初始化一次日志（避免重复 handler）。
  2. 环境变量支持：`LOG_LEVEL` 可覆盖默认 INFO（由 RichLogger 内部适配）。
- 验收标准：
  - [ ] 启动时输出美化日志，无重复 handler 现象。
  - [ ] 未捕获异常时出现富回溯样式。
  - [ ] 业务代码无 `print()`。
- 注释要求：说明“只初始化一次”的约束与原因。
- 预计耗时：0.2h

### 任务 T4：双启动方式与可配置参数
- 目标：支持两种启动方式并可通过简单方式配置 host/port/reload。
- 输入：需求文档；uvicorn 官方参数。
- 输出：README 片段或注释示例；可通过命令行/环境变量调整 HOST/PORT/RELOAD。
- 执行步骤：
  1. 在 `main.py` 提供 `__main__` 启动分支：读取 `HOST`、`PORT`、`RELOAD`（环境变量优先）。
  2. 在文档或示例中给出 uvicorn CLI 启动方式与 `--reload` 提示。
- 验收标准：
  - [ ] 直接运行入口文件可启动本地服务。
  - [ ] 使用 `uvicorn Kobe.main:app` 可启动成功。
- 注释要求：在入口处说明两种启动方式的适用场景。
- 预计耗时：0.3h

### 任务 T5：验证与测试
- 目标：提供最小验证与可选自动化测试思路。
- 输入：已实现的入口与路由。
- 输出：访问与断言步骤；可选简单测试脚本（如后续再补）。
- 执行步骤：
  1. 启动服务后访问 `http://127.0.0.1:8000/health`，确认 200 与 JSON 内容。
  2. 观察日志输出样式，确认无重复 handler。
- 验收标准：
  - [ ] 健康检查返回契约一致。
  - [ ] 日志与回溯样式符合预期。
- 注释要求：N/A（测试说明即可）。
- 预计耗时：0.3h

### 任务 T6：文档与使用示例
- 目标：在项目 `Kobe/Readme.md` 区域补充运行指引与注意事项。
- 输入：本次实现细节。
- 输出：使用示例命令与注意事项（venv 使用、生产禁用 reload、遵循统一日志规范）。

- 验收标准：
  - [ ] 文档包含直接运行与 uvicorn CLI 两种方式。
  - [ ] 强调 `Kobe/.venv` 环境与日志规范。
- 注释要求：N/A。
- 预计耗时：0.2h

## 整体验收标准
- [ ] 所有任务完成并可通过本地最小验证。
- [ ] 符合 BackendConstitution（Python 3.10、统一日志、禁止 print、使用 venv）。
- [ ] 注释符合 CodeCommentStandard（行动叙事式注释）。
- [ ] 文档完整：包含运行方式、参数说明与注意事项。

