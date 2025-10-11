# Kobe 项目使用与开发指南

## 简介
- Kobe 是一个以 Python 3.10 为基线的后端项目，默认在虚拟环境 `Kobe/.venv` 中运行。
- 日志统一由 `Kobe/SharedUtility/RichLogger` 提供美化与异常回溯，业务代码禁止使用 `print()` 输出日志。
- 提供最小可运行的 FastAPI 程序入口 `Kobe/main.py`，用于快速启动与健康检查闭环。

## 环境要求
- Python: 3.10（严格）
- 虚拟环境：仅使用 `Kobe/.venv`
- 操作系统：Windows（示例命令基于 PowerShell）；其他系统请按等效方式替换路径与命令。

## 快速开始
### 1) 激活虚拟环境（PowerShell）
```powershell
& "D:/AI_Projects/Kobe/.venv/Scripts/Activate.ps1"
```

### 2) 安装依赖
```powershell
# 在虚拟环境内执行
pip install -r D:/AI_Projects/Kobe/Requirements.txt
```

### 3) 启动服务（两种方式）
- 直接运行入口（适合最小闭环验证）：
  ```powershell
  python D:/AI_Projects/Kobe/main.py
  ```
- 使用 uvicorn CLI（官方推荐，生产/开发统一）：
  ```powershell
  python -m uvicorn Kobe.main:app --host 127.0.0.1 --port 8000

  celery -A Kobe.SharedUtility.TaskQueue:app worker -l info --pool=gevent --concurrency=100
  # 开发热重载（仅本地开发 run from D:\AI_Projects>）：


  python -m uvicorn Kobe.main:app --host $env:UVICORN_HOST --port $env:UVICORN_PORT --reload --log-level debug
  ```

提示：直接运行 `main.py` 会在启动前将进程工作目录切换到 `Kobe/`，并且当启用热重载时仅监听 `Kobe/` 目录的文件变更（外部目录变更不会触发重启）。

### 4) 运行参数（环境变量）
- `UVICORN_HOST`：默认 `127.0.0.1`
- `UVICORN_PORT`：默认 `8000`
- `UVICORN_RELOAD`：默认 `0`（关闭），可设为 `1/true/yes/on` 开启
- `LOG_LEVEL`：默认 `INFO`

说明：当通过 `main.py` 启动并开启热重载时，文件监控范围仅限 `Kobe/` 目录。

示例（PowerShell）：
```powershell
$env:UVICORN_HOST = "0.0.0.0"
$env:UVICORN_PORT = "8080"
$env:UVICORN_RELOAD = "1"
$env:LOG_LEVEL = "DEBUG"
python D:/AI_Projects/Kobe/main.py
```

### 5) 健康检查
- 浏览器或命令行访问：`http://127.0.0.1:8000/health`
- 期望返回：
  ```json
  { "status": "ok" }
  ```
- curl 示例：
  ```powershell
  curl http://127.0.0.1:8000/health
  ```

## 日志规范（RichLogger）
- 统一入口：仅使用 `Kobe/SharedUtility/RichLogger` 进行日志初始化与异常美化。
- 初始化示例（程序入口仅调用一次）：
  ```python
  from Kobe.SharedUtility.RichLogger import init_logging, install_traceback
  init_logging(level="INFO")
  install_traceback()
  ```
- 业务模块内使用标准库 logging：
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.info("正常信息")
  logger.error("错误信息", exc_info=True)
  ```
- 禁止在业务代码中使用 `print()` 输出日志。

## 目录结构（简要）
```text
Kobe/
  Readme.md
  Requirements.txt
  main.py                # FastAPI 程序入口，暴露 app 与 /health；初始化 RichLogger
  SharedUtility/
    RichLogger/
      __init__.py
      console.py
      logger.py
      traceback_setup.py
      styles.toml
      tests/
        test_basic.py
  mango_db/
    readme.md
  TempUtility/
    ...
```

## 开发规范（关键要点）
- Python 版本：3.10
- 虚拟环境：仅使用 `Kobe/.venv` 安装与执行
- 日志：统一使用 `logging`，入口一次性初始化 RichLogger；禁用 `print()`
- 注释规范：行动叙事式注释（Action-Narrative Comments），说明“做什么/为什么/如何流转”，而非复述语法

## 常见问题（FAQ）
- Q: 导入 `fastapi` 失败？
  - A: 未激活 `Kobe/.venv` 或未安装依赖。请先激活虚拟环境并执行 `pip install -r Kobe/Requirements.txt`。
- Q: `--reload` 是否可用于生产？
  - A: 否。`--reload` 仅用于开发环境的热重载，生产环境请关闭。
- Q: 如何调整日志级别？
  - A: 设置 `LOG_LEVEL` 环境变量（如 `DEBUG/INFO/WARNING/ERROR`），入口初始化会自动读取。

## 参考
- FastAPI: https://fastapi.tiangolo.com/
- uvicorn: https://www.uvicorn.org/
- Rich: https://rich.readthedocs.io/en/stable/


{
  field_key : "xxx"
  value : {
    value1 : "..."
    value2 : "..."
    value3 : "..."
  }
}

## MySQL（Docker，本地开发）
- 目标：提供本地可用的 MySQL 8.0 实例，供样本采集与联调使用。
- 容器：`kobe-mysql`，网络：`ai_services_net`，端口映射：`3306:3306`。

命令（PowerShell）
```powershell
# 创建网络（如已存在会跳过）
if (-not (docker network ls --format '{{.Name}}' | Select-String -SimpleMatch ai_services_net)) {
  docker network create ai_services_net
}
# 拉取镜像并启动容器（第一次执行需数十秒）
$MYSQL_ROOT_PASSWORD = 'KobeDev!2025'
$MYSQL_DATABASE = 'wyc_visa_db'
docker pull mysql:8.0

docker run -d --name kobe-mysql --network ai_services_net `
  -e MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD `
  -e MYSQL_DATABASE=$MYSQL_DATABASE `
  -p 3306:3306 mysql:8.0 `
  --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

# 等待就绪（日志出现“ready for connections”）
docker logs -f kobe-mysql
```

环境变量（.env）
```env
MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="KobeDev!2025"
MYSQL_DATABASE="wyc_visa_db"
```

可选：导入已有 SQL（如 `D:/AI_Projects/Visa/visa_db.sql`）
```powershell
# 拷贝 SQL 进容器并导入（首次初始化后也可这样导入）
docker cp D:/AI_Projects/Visa/visa_db.sql kobe-mysql:/tmp/visa_db.sql

docker exec -i kobe-mysql bash -lc "mysql -uroot -p$MYSQL_ROOT_PASSWORD $MYSQL_DATABASE < /tmp/visa_db.sql"
```
