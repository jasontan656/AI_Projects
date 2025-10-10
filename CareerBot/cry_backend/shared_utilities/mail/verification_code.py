from __future__ import annotations
from shared_utilities.mail.SendMail import send_email


async def send_verification_email(to: str, code: str, is_test_user: bool = False) -> bool:
    subject = "Email verification code - verify your identity"
    # subject 赋值为邮件主题字符串
    # 返回值供调用方判断发送是否成功

    if is_test_user:
        body = (
            f"Your verification code is: {code}\n\n"
            "This is a test code. Valid for 5 minutes."
        )
        # body 赋值为测试用户正文，提示固定验证码与有效期
    else:
        body = (
            f"Your verification code is: {code}\n\n"
            "The code is valid for 5 minutes. Please use it promptly."
        )
        # body 赋值为正式用户正文，提示5分钟有效

    return await send_email(to=to, subject=subject, body=body, content_type="plain")
    # send_email(...) 发送邮件，传入to/subject/body/content_type
    # 返回bool表示是否成功，供上层统一响应


# ======== Testing utilities (non-production) ========
def generate_verification_code(length: int = 6) -> str:
    """生成指定位数的数字验证码（默认6位）。"""
    import random
    return ''.join(str(random.randint(0, 9)) for _ in range(length))


def get_test_verification_code(length: int = 6) -> str:
    """测试场景直接获取随机验证码（不发送邮件）。"""
    return generate_verification_code(length)

