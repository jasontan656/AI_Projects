"""RichLogger 使用示例 - 展示如何在你的模块中使用漂亮的日志输出"""

# ============================================================
# 方式 1：标准日志输出（最常用）
# ============================================================
from Kobe.SharedUtility.RichLogger import init_logging
import logging

def example_basic_logging():
    """基础日志使用示例"""
    # 1. 初始化日志系统（程序启动时调用一次）
    init_logging(level="DEBUG")  # 设置日志级别
    
    # 2. 获取 logger（按照 Python 标准写法）
    logger = logging.getLogger(__name__)
    
    # 3. 像平常一样使用 logging，但输出会变得漂亮！
    logger.debug("🔍 调试信息：正在检查数据...")
    logger.info("✅ 普通信息：程序启动成功")
    logger.warning("⚠️ 警告：配置文件使用了默认值")
    logger.error("❌ 错误：无法连接到数据库")
    
    # 4. 带变量的日志（推荐使用格式化）
    user_name = "张三"
    user_age = 25
    logger.info(f"用户登录：{user_name}，年龄：{user_age}")


# ============================================================
# 方式 2：使用 Rich Console 进行更丰富的输出
# ============================================================
from Kobe.SharedUtility.RichLogger import get_console

def example_rich_console():
    """使用 Console 进行更丰富的终端输出"""
    # 获取 Console 对象
    console = get_console()
    
    # 输出彩色文本（支持 Rich 的 markup 语法）
    console.print("[bold green]成功![/bold green] 数据已保存")
    console.print("[bold red]错误![/bold red] 文件不存在")
    console.print("[yellow]警告:[/yellow] 磁盘空间不足")
    
    # 输出表格
    from rich.table import Table
    table = Table(title="用户信息")
    table.add_column("姓名", style="cyan")
    table.add_column("年龄", style="magenta")
    table.add_row("张三", "25")
    table.add_row("李四", "30")
    console.print(table)
    
    # 输出 JSON 数据（自动格式化和高亮）
    from rich.json import JSON
    data = {"name": "张三", "age": 25, "city": "北京"}
    console.print(JSON.dumps(data))


# ============================================================
# 方式 3：完整配置（带文件输出）
# ============================================================
def example_full_config():
    """完整配置示例：同时输出到终端和文件"""
    init_logging(
        level="DEBUG",           # 日志级别
        markup=True,            # 启用 Rich 标记语法
        logfile="app.log"       # 同时保存到文件
    )
    
    logger = logging.getLogger(__name__)
    logger.info("日志会同时显示在终端（漂亮格式）和文件（纯文本）中")


# ============================================================
# 方式 4：美化异常输出
# ============================================================
from Kobe.SharedUtility.RichLogger import install_traceback

def example_traceback():
    """安装美化的异常追踪"""
    # 安装 traceback 美化（程序启动时调用一次）
    install_traceback(show_locals=True)  # show_locals=True 会显示局部变量
    
    # 现在当程序出错时，会显示漂亮的异常信息
    try:
        result = 10 / 0  # 故意触发异常
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("计算出错")


# ============================================================
# 实际使用场景示例
# ============================================================
def your_business_function():
    """模拟你的业务函数"""
    logger = logging.getLogger(__name__)
    
    logger.info("开始处理数据...")
    
    try:
        # 你的业务逻辑
        data = {"user": "张三", "action": "登录"}
        logger.debug(f"接收到数据：{data}")
        
        # 模拟处理
        result = process_data(data)
        
        logger.info(f"处理完成，结果：{result}")
        return result
    
    except Exception as e:
        logger.error(f"处理失败：{e}", exc_info=True)  # exc_info=True 会显示完整堆栈
        raise

def process_data(data):
    """模拟数据处理"""
    return f"已处理 {data['user']} 的 {data['action']}"


# ============================================================
# 程序入口示例
# ============================================================
if __name__ == "__main__":
    # 在程序入口初始化一次
    init_logging(level="DEBUG")
    install_traceback()
    
    print("\n=== 示例 1: 基础日志输出 ===")
    example_basic_logging()
    
    print("\n=== 示例 2: Rich Console 输出 ===")
    example_rich_console()
    
    print("\n=== 示例 3: 业务函数中使用 ===")
    your_business_function()
    
    print("\n✅ 所有示例运行完成！")

