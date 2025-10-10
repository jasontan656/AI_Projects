# RichLogger - 让你的日志输出更漂亮

> **一句话介绍**：让 Python 程序在终端输出彩色、格式化的日志，替代丑陋的纯文本输出。

## 🎯 这个工具是干什么的？

普通的 Python 日志输出是这样的：
```
2024-01-01 10:00:00 INFO 用户登录成功
2024-01-01 10:00:01 ERROR 数据库连接失败
```

使用 RichLogger 后是这样的：
- ✅ 不同级别的日志有不同颜色（INFO 蓝色，ERROR 红色等）
- ✅ 异常信息格式化显示，更容易看懂
- ✅ 支持表格、JSON 等丰富格式
- ✅ 自动添加时间戳和行号

## 🚀 快速上手（3 步走）

### 第 1 步：在程序入口初始化（只需一次）

在你的 `main.py` 或程序启动文件中添加：

```python
from Kobe.SharedUtility.RichLogger import init_logging, install_traceback

# 初始化日志系统
init_logging(level="INFO")  # 可选: level="DEBUG" 显示更多信息

# 美化异常显示（可选但推荐）
install_traceback()
```

### 第 2 步：在业务模块中使用标准 logging

在你的任何业务代码中，像平常一样使用 Python 标准 `logging`：

```python
import logging

logger = logging.getLogger(__name__)

# 输出日志（会自动变漂亮！）
logger.debug("调试信息：正在检查数据...")
logger.info("用户登录成功")
logger.warning("配置文件缺失，使用默认值")
logger.error("数据库连接失败")
```

### 第 3 步：运行你的程序

```bash
# 使用虚拟环境运行
D:/AI_Projects/Kobe/.venv/Scripts/python.exe your_script.py
```

就这么简单！你的日志输出会自动变得漂亮且易读。

## 📖 完整示例

### 示例 1：最简单的使用

```python
# my_app.py
from Kobe.SharedUtility.RichLogger import init_logging
import logging

# 初始化
init_logging(level="INFO")

# 使用
logger = logging.getLogger(__name__)
logger.info("程序启动成功")
logger.error("出现了一个错误")
```

运行：
```bash
D:/AI_Projects/Kobe/.venv/Scripts/python.exe my_app.py
```

### 示例 2：同时输出到文件

```python
from Kobe.SharedUtility.RichLogger import init_logging

# 日志同时显示在终端（漂亮）和保存到文件（纯文本）
init_logging(level="DEBUG", logfile="app.log")
```

### 示例 3：捕获异常时显示详细信息

```python
import logging
logger = logging.getLogger(__name__)

try:
    result = 10 / 0
except Exception as e:
    # exc_info=True 会显示完整的异常堆栈
    logger.error("计算出错", exc_info=True)
```

## 🔧 高级功能（可选）

### 使用 Rich Console 进行更丰富的输出

如果你需要输出表格、进度条等，可以使用 `get_console()`：

```python
from Kobe.SharedUtility.RichLogger import get_console

console = get_console()

# 输出彩色文本
console.print("[bold green]成功![/bold green] 数据已保存")
console.print("[bold red]错误![/bold red] 文件不存在")

# 输出表格
from rich.table import Table
table = Table(title="用户信息")
table.add_column("姓名", style="cyan")
table.add_column("年龄", style="magenta")
table.add_row("张三", "25")
console.print(table)
```

### 查看完整示例

运行内置的示例文件查看更多用法：
```bash
D:/AI_Projects/Kobe/.venv/Scripts/python.exe D:/AI_Projects/Kobe/SharedUtility/RichLogger/example_usage.py
```

## ⚙️ 配置选项

### 日志级别

```python
init_logging(level="DEBUG")   # 显示所有日志（包括调试信息）
init_logging(level="INFO")    # 显示一般信息及以上（推荐）
init_logging(level="WARNING") # 只显示警告和错误
init_logging(level="ERROR")   # 只显示错误
```

### 文件输出

```python
# 同时输出到终端和文件
init_logging(level="INFO", logfile="app.log")

# 文件中的日志是纯文本格式，方便检索和分析
```

### 环境变量（可选）

可以通过环境变量控制行为：

- `RICH_NO_COLOR=1` - 禁用彩色输出（适合 CI/CD 环境）
- `RICH_THEME=high_contrast` - 使用高对比度主题
- `LOG_LEVEL=DEBUG` - 设置日志级别

## ❓ 常见问题

### Q: 我可以在多个模块中使用吗？

**A:** 可以！只需要在程序入口初始化一次，所有模块都能使用：

```python
# main.py（只在这里初始化）
from Kobe.SharedUtility.RichLogger import init_logging
init_logging(level="INFO")

# module_a.py（直接使用标准 logging）
import logging
logger = logging.getLogger(__name__)
logger.info("模块 A 的日志")

# module_b.py（直接使用标准 logging）
import logging
logger = logging.getLogger(__name__)
logger.info("模块 B 的日志")
```

### Q: 我还可以用 print() 吗？

**A:** 可以用，但**不推荐用于日志输出**。统一使用 `logging` 更规范：
- ✅ 可以控制日志级别（开发时显示 DEBUG，生产环境只显示 ERROR）
- ✅ 可以同时输出到文件
- ✅ 可以添加时间戳、行号等元信息
- ✅ 符合 Python 最佳实践

### Q: 如何在生产环境使用？

**A:** 建议关闭彩色输出，并将日志写入文件：

```python
# 生产环境配置
init_logging(
    level="WARNING",  # 只记录警告和错误
    logfile="/var/log/myapp.log"  # 输出到日志文件
)
```

或设置环境变量：
```bash
export RICH_NO_COLOR=1
export LOG_LEVEL=WARNING
```

## 📋 API 参考

### `init_logging(level, markup, logfile)`

初始化日志系统。

**参数：**
- `level` (str, 可选): 日志级别，如 "DEBUG", "INFO", "WARNING", "ERROR"
- `markup` (bool, 默认 True): 是否启用 Rich 标记语法
- `logfile` (str, 可选): 日志文件路径，如果提供则同时输出到文件

**示例：**
```python
init_logging(level="INFO", logfile="app.log")
```

### `install_traceback(show_locals, width, theme)`

安装美化的异常追踪显示。

**参数：**
- `show_locals` (bool, 默认 False): 是否显示局部变量
- `width` (int, 可选): 显示宽度
- `theme` (str, 可选): 主题名称

**示例：**
```python
install_traceback(show_locals=True)
```

### `get_console()`

获取 Console 对象，用于更丰富的输出。

**示例：**
```python
console = get_console()
console.print("[bold]粗体文本[/bold]")
```

### `init_console(options)`

初始化 Console（通常不需要手动调用）。

**参数：**
- `options` (dict, 可选): 配置选项，如 `{"no_color": True, "theme": "high_contrast"}`

## 🔗 相关资源

- **完整示例代码**: `Kobe/SharedUtility/RichLogger/example_usage.py`
- **测试文件**: `Kobe/SharedUtility/RichLogger/tests/test_basic.py`
- **项目规范**: `CodexFeatured/Common/BackendConstitution.md`

## 💡 最佳实践

1. ✅ **在程序入口初始化一次**，不要在每个模块中重复初始化
2. ✅ **使用标准 logging**，不要用 `print()` 输出日志
3. ✅ **使用合适的日志级别**：DEBUG（调试）、INFO（一般信息）、WARNING（警告）、ERROR（错误）
4. ✅ **捕获异常时使用 `exc_info=True`**，显示完整堆栈信息
5. ✅ **生产环境输出到文件**，便于后续分析

---

**需要帮助？** 运行示例文件查看更多用法：
```bash
D:/AI_Projects/Kobe/.venv/Scripts/python.exe D:/AI_Projects/Kobe/SharedUtility/RichLogger/example_usage.py
```
