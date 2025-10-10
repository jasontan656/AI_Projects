# 自定义异常类定义
# 继承自 Exception 基类，用于用户注册相关错误处理


class UserAlreadyExistsError(Exception):
    """
    用户已存在异常

    当尝试注册的用户（用户名或邮箱）已在系统中存在时抛出此异常。
    调用方可通过捕获此异常来处理重复注册的情况。
    """
    pass


class InvalidInputError(Exception):
    """
    输入数据无效异常

    当注册输入数据不符合校验规则时抛出此异常。
    包括用户名长度、密码强度、邮箱格式等校验失败的情况。
    """
    pass


class InvalidCredentialsError(Exception):
    """
    登录凭证无效异常

    当用户提供的用户名或密码不正确时抛出此异常。
    用于标准登录流程中的凭证验证失败情况。
    """
    pass


class EmailAlreadyRegisteredError(Exception):
    """
    邮箱已注册异常类

    当用户尝试使用已注册且设置密码的邮箱再次注册时抛出此异常。
    用于区分OAuth用户（允许补设密码）和已完整注册用户（禁止重复注册）。
    """
    pass
class DependencyError(Exception):
    """
    External dependency failure (e.g., database unavailability).
    Signals callers to map to DEPENDENCY_ERROR responses.
    """
    pass
