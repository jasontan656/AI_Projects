# FastAPI 程序入口与日志闭环需求说明

## 背景与目标

- 目标：为现有项目新增一个清晰的程序入口 `Kobe/main.py`，基于 FastAPI 与 uvicorn 启动可访问的本地 HTTP 服务；在应用启动阶段调用一次 RichLogger 完成统一日志初始化，形成“能启动、能输出日志、能返回健康检查”的最小闭环，便于后续迭代。
- 约束与遵循：严格遵循《BackendConstitution》中的技术栈与日志规范（Python 3.10；仅使用虚拟环境 `Kobe/.venv`；仅用 `Kobe/SharedUtility/RichLogger` 统一初始化日志；业务代码禁止 `print()`）。

## 用户视角功能需求

- 启动服务：用户通过运行程序入口即可启动一个本地 HTTP 服务，默认监听 `127.0.0.1:8000`。
- 健康检查：访问 `GET /health` 可快速确认服务是否正常，返回简洁 JSON 结果（如 `{"status":"ok"}`）。
- 日志闭环：程序启动时自动初始化一次美化日志（RichLogger），后续模块用标准 `logging` 产生日志；未捕获异常有美化的回溯输出，便于排错。
- 易用配置：用户可用“简单方式”调整主机、端口与开发热重载开关（如命令行参数或环境变量），无需理解实现细节。
- 双启动模式：
  - 直接运行入口文件（适合本地最小闭环验证）。
  - 使用 `uvicorn` CLI 指定 ASGI 应用（官方推荐做法，便于生产/开发统一）。

## 行为规则与输入/输出约束

- 路由与方法：
  - `GET /health`：无需鉴权；用于服务自检和集成环境健康探测。
- 返回数据：
  - 成功：HTTP 200；Body 为 `{"status":"ok"}`，字段语义清晰、稳定。
- 启动参数（建议约定，不绑定实现细节）：
  - `HOST`：默认 `127.0.0.1`，允许通过环境变量或启动参数覆盖。
  - `PORT`：默认 `8000`，允许通过环境变量或启动参数覆盖。
  - `RELOAD`：默认关闭；开发模式可启用（仅本地开发使用）。
  - `LOG_LEVEL`：默认 `INFO`；遵循 BackendConstitution，通过环境变量或统一初始化控制。

## 结构与变更决策

### 新增目录/文件

```text
Kobe/
  main.py              # 程序入口：定义 FastAPI 实例与 /health 路由；调用 RichLogger 完成一次性初始化
```

- 目的与放置理由：
  - 入口文件位于 `Kobe/` 顶层便于被 `uvicorn` 以模块路径 `Kobe.main:app` 直接发现与运行；与既有 `Kobe/SharedUtility/RichLogger` 相邻，减少相对导入复杂度。
  - 使用最小化单文件入口，后续可按业务增长迁移到分层目录（如 `Kobe/app/routers` 等）。

### 修改现有文件

- `Kobe/Requirements.txt`
  - 变更类型：能力补充（新增依赖）。
  - 修改内容：新增 `fastapi` 与 `uvicorn[standard]`（官方推荐 extras，包含更快的可选依赖）。
  - 原因：支持 FastAPI 应用与 ASGI 服务器运行，满足“程序入口 + 可运行服务”的闭环需求。

（说明）`CodexFeatured/Common/CodebaseStructure.md` 由脚本生成与更新；新增 `Kobe/main.py` 落地后，运行脚本会自动反映，无需手改。

## 对齐官方规范与最佳实践

- FastAPI 官方：
  - 推荐将应用实例命名为 `app`，便于 `uvicorn` 使用 `模块路径:app` 约定启动。
  - 路由应清晰稳定；以 `GET /health` 作为健康检查端点符合通用约定。
- uvicorn 官方：
  - 推荐使用 CLI 启动（生产/开发皆可统一）：`uvicorn Kobe.main:app --host 127.0.0.1 --port 8000`。
  - 开发模式下可使用 `--reload` 自动热重载；生产环境禁用。
- 日志与异常：
  - 统一由 `Kobe/SharedUtility/RichLogger` 初始化根日志器；业务模块仅用标准 `logging`。
  - 使用富回溯（traceback）提升排错体验，同时限制在入口处只调用一次初始化，避免重复添加 handler。

## 运行方式（面向使用者）

- 直接运行（适合最小闭环验证）：
  - `Kobe/.venv/Scripts/python.exe Kobe/main.py`
- 使用 uvicorn CLI（官方推荐，生产/开发统一）：
  - `Kobe/.venv/Scripts/python.exe -m uvicorn Kobe.main:app --host 127.0.0.1 --port 8000`
  - 开发热重载：追加 `--reload`

（提示）请确保命令在虚拟环境 `Kobe/.venv` 中执行，或已激活该环境。

## 验收标准

- 启动后访问 `http://127.0.0.1:8000/health` 返回 200，Body 为 `{"status":"ok"}`。
- 启动日志与访问日志为美化样式（Rich），无重复 handler 现象；业务代码未使用 `print()`。
- 程序入口日志初始化仅调用一次；未捕获异常可见富回溯样式。

## 兼容性与约束

- Python 版本固定为 3.10（项目统一标准）。
- 仅允许使用 `Kobe/.venv` 虚拟环境安装与执行依赖与命令。
- 若后续引入更多路由与中间件，应保持入口文件职责单一，逐步迁移到模块化目录结构（不在本次范围）。

## 后续扩展建议（非本次范围）

- 配置管理：引入 `pydantic-settings`，规范化 HOST/PORT/RELOAD/LOG_LEVEL 读取；支持 `.env` 与环境变量多源合并。
- 结构化日志：结合 `structlog` 输出 JSON/键值日志，便于采集与检索（与 Rich 终端输出互补）。
- 运行管理：新增 Makefile/PowerShell 脚本封装常用命令（启动、热重载、测试）。

## 变更清单（汇总）

- 新增
  - `Kobe/main.py`：程序入口；定义 `app` 与 `/health`；初始化 RichLogger；支持直接运行与 `uvicorn` 启动。
- 修改
  - `Kobe/Requirements.txt`（能力补充）：新增 `fastapi`、`uvicorn[standard]`。

## 不新增的内容与理由

- 不新增多层目录结构（如 `Kobe/app/routers` 等）：当前仅实现最小可用闭环，一个入口文件即可；避免过度设计，降低首轮上手成本。
- 不新增配置文件模板：配置项较少，先通过环境变量/启动参数满足；待复杂度提升再引入专用配置方案（见“后续扩展建议”）。

