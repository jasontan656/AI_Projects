# 邮件功能包初始化
# 导出邮件发送和模板管理的核心功能

# from .SendMail 导入传统邮件发送功能
from .SendMail import (
    send_email,
    EmailMessage,
    MailSender,
    mail_sender,
    mail_settings
)

# from .SendMail 导入新增的模板和批量发送功能  
from .SendMail import (
    send_template_email,
    send_bulk_email,
    send_bulk_template_email
)

# from .TemplateManager 导入模板管理功能
try:
    from .TemplateManager import (
        TemplateManager,
        mail_template_manager
    )
    TEMPLATE_MANAGER_AVAILABLE = True
except ImportError:
    TEMPLATE_MANAGER_AVAILABLE = False

# __all__ 列表定义包的公共接口，控制 from shared_utilities.mail import * 的行为
__all__ = [
    # 传统邮件发送功能
    'send_email',
    'EmailMessage', 
    'MailSender',
    'mail_sender',
    'mail_settings',
    
    # 新增模板和批量功能
    'send_template_email',
    'send_bulk_email', 
    'send_bulk_template_email',
    
    # 模板管理功能
    'TemplateManager',
    'mail_template_manager',
    
    # 功能可用性标识
    'TEMPLATE_MANAGER_AVAILABLE'
]


