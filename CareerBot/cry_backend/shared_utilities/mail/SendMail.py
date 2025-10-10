# 导入标准库模块
from typing import Optional, List, Union, Dict, Any
import asyncio
from pathlib import Path

# 导入第三方库模块
from pydantic_settings import BaseSettings
from aiosmtplib import send
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# 模板引擎
try:
    from jinja2 import Environment, FileSystemLoader, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("Warning: jinja2 not installed. Template functionality will be limited.")

# 导入模板管理器
try:
    from .TemplateManager import mail_template_manager
    TEMPLATE_MANAGER_AVAILABLE = True
except ImportError:
    TEMPLATE_MANAGER_AVAILABLE = False
    print("Warning: TemplateManager not available. Template functionality will be disabled.")


class MailSettings(BaseSettings):
    """
    邮件配置类

    管理邮件服务器相关的环境变量配置。
    通过 pydantic.BaseSettings 自动从 .env 文件加载配置。
    """

    # 邮件服务器配置
    mail_host: str
    mail_port: int
    mail_username: str
    mail_password: str
    mail_encryption: str
    mail_from_address: str
    mail_from_name: str
    mail_timeout: float = 5.0

    class Config:
        """
        Pydantic 配置类

        指定环境变量加载的配置文件路径。
        """
        # 使用绝对路径确保能找到.env文件
        # 当前文件位于 utilities/mail/SendMail.py
        # 向上三级目录可定位到 cry_backend 目录
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        extra = "ignore"  # 忽略.env文件中的额外字段


# 创建全局邮件配置实例
# 通过 MailSettings() 自动从 .env 文件加载配置
# 结果赋值给 mail_settings 变量，提供给其他模块使用
mail_settings = MailSettings()


class EmailMessage:
    """
    邮件消息类

    用于构建邮件消息，包含主题、收件人、正文等信息。
    支持传统的直接内容方式和基于模板的动态内容生成。
    """

    def __init__(self,
                 to: Union[str, List[str]],
                 subject: str,
                 body: Optional[str] = None,
                 content_type: str = 'plain',
                 template_name: Optional[str] = None,
                 template_vars: Optional[Dict[str, Any]] = None):
        """
        初始化邮件消息

        支持两种初始化方式：
        1. 传统方式：直接提供邮件正文内容
        2. 模板方式：提供模板名称和变量进行动态生成

        参数:
            to (Union[str, List[str]]): 收件人邮箱地址，可以是单个字符串或列表
            subject (str): 邮件主题
            body (Optional[str]): 邮件正文内容，可选
            content_type (str): 内容类型，默认为 'plain'，也可以是 'html'
            template_name (Optional[str]): 模板名称，可选
            template_vars (Optional[Dict[str, Any]]): 模板变量字典，可选
        """
        # isinstance 函数通过传入 to 和 str 类型检查收件人类型
        # 如果是字符串则转换为列表，否则直接使用，结果赋值给 self.to
        self.to = [to] if isinstance(to, str) else to

        # subject 参数直接赋值给 self.subject 变量
        self.subject = subject

        # template_name 参数赋值给 self.template_name 变量
        # 用于标识是否使用模板模式
        self.template_name = template_name
        
        # template_vars 参数赋值给 self.template_vars 变量
        # 如果为None则初始化为空字典，用于模板变量替换
        self.template_vars = template_vars or {}

        # content_type 参数赋值给 self.content_type 变量
        self.content_type = content_type

        # self.attachments 被初始化为空列表，用于存储邮件附件
        self.attachments = []

        # _prepare_content 方法被调用，用于准备最终的邮件内容
        # 根据是否使用模板模式决定内容生成方式
        self._prepare_content(body)
    
    def add_attachment_from_file(self, file_path: str):
        """
        从文件路径添加附件到邮件中
        
        读取文件内容并创建MIME附件对象添加到邮件。
        
        参数:
            file_path: 附件文件的完整路径
            
        异常:
            FileNotFoundError: 文件不存在时抛出
            ValueError: 文件格式不支持时抛出
        """
        # Path 构造函数通过传入文件路径创建路径对象
        file_path_obj = Path(file_path)
        
        # file_path_obj.exists 方法检查文件是否存在
        if not file_path_obj.exists():
            # raise 语句抛出FileNotFoundError异常，传入文件路径
            raise FileNotFoundError(f"Attachment file not found: {file_path}")
        
        # file_path_obj.stat 方法获取文件统计信息
        file_stat = file_path_obj.stat()
        
        # file_stat.st_size 属性获取文件大小字节数
        file_size = file_stat.st_size
        
        # file_size / (1024 * 1024) 计算文件大小的MB值
        file_size_mb = file_size / (1024 * 1024)
        
        # if 条件检查文件是否超过20MB阈值
        if file_size_mb > 20:
            # print 函数输出大文件警告信息，包含文件名和大小（英文ASCII）
            print(f"LARGE_ATTACHMENT_WARNING: {file_path_obj.name} ({file_size_mb:.1f}MB)")
        
        # _get_mime_type 方法通过传入文件路径获取MIME类型
        # 结果赋值给 mime_type 变量
        main_type, sub_type = self._get_mime_type(file_path)
        
        # open 函数通过传入文件路径和二进制读取模式打开文件
        with open(file_path, 'rb') as f:
            # f.read 方法读取文件的所有二进制内容
            file_data = f.read()
        
        # MIMEBase 构造函数通过传入主类型和子类型创建MIME对象
        # 结果赋值给 attachment 变量
        attachment = MIMEBase(main_type, sub_type)
        
        # attachment.set_payload 方法通过传入文件数据设置附件内容
        attachment.set_payload(file_data)
        
        # encoders.encode_base64 函数通过传入附件对象
        # 对附件内容进行Base64编码
        encoders.encode_base64(attachment)
        
        # file_path_obj.name 属性获取文件名
        filename = file_path_obj.name
        
        # attachment.add_header 方法通过传入Content-Disposition头和文件名
        # 设置附件的下载文件名
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="{filename}"'
        )
        
        # self.attachments.append 方法将构建的附件对象添加到附件列表
        self.attachments.append(attachment)
    
    def _get_mime_type(self, file_path: str) -> tuple[str, str]:
        """
        根据文件扩展名获取MIME类型
        
        返回MIME主类型和子类型的元组，支持常见文件格式。
        
        参数:
            file_path: 文件路径
            
        返回值:
            tuple[str, str]: (主类型, 子类型)
        """
        # Path 构造函数通过传入文件路径创建路径对象
        file_path_obj = Path(file_path)
        
        # file_path_obj.suffix.lower 方法获取小写的文件扩展名
        file_extension = file_path_obj.suffix.lower()
        
        # mime_types 字典映射文件扩展名到MIME类型元组
        # 扩展支持更多常见文件格式
        mime_types = {
            # 文档类型
            '.pdf': ('application', 'pdf'),
            '.doc': ('application', 'msword'),
            '.docx': ('application', 'vnd.openxmlformats-officedocument.wordprocessingml.document'),
            '.txt': ('text', 'plain'),
            '.rtf': ('application', 'rtf'),
            
            # 压缩包类型
            '.zip': ('application', 'zip'),
            '.rar': ('application', 'x-rar-compressed'),
            '.7z': ('application', 'x-7z-compressed'),
            '.tar': ('application', 'x-tar'),
            '.gz': ('application', 'gzip'),
            
            # 图片类型  
            '.jpg': ('image', 'jpeg'),
            '.jpeg': ('image', 'jpeg'),
            '.png': ('image', 'png'),
            '.gif': ('image', 'gif'),
            '.bmp': ('image', 'bmp'),
            '.tiff': ('image', 'tiff'),
            '.webp': ('image', 'webp'),
            
            # 表格类型
            '.xlsx': ('application', 'vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            '.xls': ('application', 'vnd.ms-excel'),
            '.csv': ('text', 'csv'),
            
            # 演示文稿类型
            '.pptx': ('application', 'vnd.openxmlformats-officedocument.presentationml.presentation'),
            '.ppt': ('application', 'vnd.ms-powerpoint'),
            
            # 音视频类型
            '.mp3': ('audio', 'mpeg'),
            '.mp4': ('video', 'mp4'),
            '.wav': ('audio', 'wav'),
            '.avi': ('video', 'x-msvideo')
        }
        
        # mime_types.get 方法通过传入文件扩展名获取MIME类型
        # 如果扩展名不在字典中则返回默认的二进制流类型
        mime_type = mime_types.get(file_extension, ('application', 'octet-stream'))
        
        # print 函数输出MIME类型信息用于调试
        print(f"   Type for {file_path_obj.name}: {mime_type[0]}/{mime_type[1]}")
        
        # return 语句返回MIME类型元组
        return mime_type
    
    def add_attachments_from_directory(self, attachments_dir: str) -> Dict[str, Any]:
        """
        从指定目录扫描并添加所有附件文件
        
        遍历目录中的所有文件，自动添加为邮件附件。
        
        参数:
            attachments_dir: 附件目录路径
            
        返回值:
            Dict[str, Any]: 附件扫描结果统计
            
        异常:
            FileNotFoundError: 目录不存在时抛出
        """
        # Path 构造函数通过传入目录路径创建路径对象
        dir_path = Path(attachments_dir)
        
        # dir_path.exists 方法检查目录是否存在
        if not dir_path.exists():
            # raise 语句抛出FileNotFoundError异常，传入目录路径
            raise FileNotFoundError(f"Attachments directory does not exist: {attachments_dir}")
        
        # dir_path.is_dir 方法检查路径是否为目录
        if not dir_path.is_dir():
            # raise 语句抛出ValueError异常，提示路径不是目录
            raise ValueError(f"Specified path is not a directory: {attachments_dir}")
        
        # 初始化统计变量
        # attachment_files 被初始化为空列表，存储找到的附件文件信息
        attachment_files = []
        
        # total_size 被初始化为0，统计附件总大小
        total_size = 0
        
        # skipped_files 被初始化为空列表，存储跳过的文件名
        skipped_files = []
        
        print(f"Scanning attachments directory: {attachments_dir}")
        
        # dir_path.iterdir 方法获取目录中所有文件和子目录的迭代器
        for file_path in dir_path.iterdir():
            # file_path.is_file 方法检查是否为普通文件
            if file_path.is_file():
                # file_path.name 属性获取文件名
                filename = file_path.name
                
                # _should_skip_file 方法通过传入文件名检查是否应跳过
                if self._should_skip_file(filename):
                    # skipped_files.append 方法将跳过的文件名添加到列表
                    skipped_files.append(filename)
                    continue
                
                # file_path.stat 方法获取文件统计信息
                file_stat = file_path.stat()
                
                # file_stat.st_size 属性获取文件大小字节数
                file_size = file_stat.st_size
                
                # file_size / (1024 * 1024) 计算文件大小的MB值
                file_size_mb = file_size / (1024 * 1024)
                
                # attachment_files.append 方法将文件信息字典添加到列表
                attachment_files.append({
                    'path': str(file_path),
                    'name': filename,
                    'size': file_size,
                    'size_mb': file_size_mb
                })
                
                # total_size 累加当前文件的大小
                total_size += file_size
                
                try:
                    # add_attachment_from_file 方法通过传入文件路径
                    # 将文件添加为邮件附件
                    self.add_attachment_from_file(str(file_path))
                    
                    # print 函数输出成功添加附件的信息
                    print(f"   Added attachment: {filename} ({file_size_mb:.1f}MB)")
                    
                except Exception as e:
                    # print 函数输出添加附件失败的详细错误信息
                    print(f"   Failed to add attachment {filename}: {type(e).__name__}: {e}")
                    
                    # skipped_files.append 方法将失败的文件添加到跳过列表
                    skipped_files.append(filename)
        
        # total_size_mb 通过除法计算总大小的MB值
        total_size_mb = total_size / (1024 * 1024)
        
        # 检查附件总大小是否超过12MB限制
        MAX_ATTACHMENT_SIZE_MB = 12.0
        if total_size_mb > MAX_ATTACHMENT_SIZE_MB:
            print(f"Total attachments size ({total_size_mb:.1f}MB) exceeds limit ({MAX_ATTACHMENT_SIZE_MB}MB)")
            print(f"Please reduce attachment file sizes")
            raise ValueError(f'Total attachments size ({total_size_mb:.1f}MB) exceeds limit ({MAX_ATTACHMENT_SIZE_MB}MB)')
        
        # print 函数输出附件扫描结果统计
        print(f"Total attachments size: {total_size_mb:.1f}MB")
        
        # if 条件检查跳过文件列表是否非空
        if skipped_files:
            # print 函数输出跳过的文件列表
            print(f"Skipped files: {', '.join(skipped_files)}")
        
        # return 语句返回附件扫描结果统计字典
        return {
            'total_files': len(attachment_files),
            'total_size_mb': total_size_mb,
            'attachment_files': attachment_files,
            'skipped_files': skipped_files
        }
    
    def _should_skip_file(self, filename: str) -> bool:
        """
        判断文件是否应该跳过不作为附件
        
        检查文件名模式，排除临时文件和系统文件。
        
        参数:
            filename: 文件名
            
        返回值:
            bool: 应该跳过返回True
        """
        # filename.lower 方法将文件名转换为小写字母
        filename_lower = filename.lower()
        
        # 定义应跳过的文件模式列表
        skip_patterns = [
            '.tmp', '.temp', '.cache', '.log',
            '.ds_store', 'thumbs.db', '.gitkeep',
            '~', '.bak', '.backup'
        ]
        
        # for pattern in skip_patterns 遍历跳过模式列表
        for pattern in skip_patterns:
            # filename_lower.endswith 方法检查文件名是否以模式结尾
            # 或 filename_lower.startswith 检查是否以模式开头
            if filename_lower.endswith(pattern) or filename_lower.startswith(pattern):
                return True
        
        # 没有匹配跳过模式时返回False
        return False
        
    def _prepare_content(self, body: Optional[str]):
        """
        准备邮件内容
        
        根据初始化参数决定使用直接内容还是模板渲染内容。
        优先级：直接提供的body > 模板渲染 > 空内容
        
        参数:
            body: 直接提供的邮件正文内容
        """
        # if 条件检查是否直接提供了邮件正文内容
        if body:
            # body 参数直接赋值给 self.body 变量
            # 使用传统的直接内容方式
            self.body = body
        # elif 条件检查是否提供了模板名称且模板管理器可用
        elif self.template_name and TEMPLATE_MANAGER_AVAILABLE:
            # try 块开始尝试渲染模板内容，捕获可能的异常
            try:
                # mail_template_manager.render_template 方法通过传入
                # 模板名称、变量字典和内容类型渲染模板
                # 结果赋值给 self.body 变量
                self.body = mail_template_manager.render_template(
                    self.template_name,
                    self.template_vars,
                    self.content_type
                )
            # except 捕获模板渲染过程中的所有异常
            except Exception as e:
                # self.body 被设定为包含错误信息的默认内容
                # 确保邮件发送不会因模板问题而完全失败
                self.body = f"Email content generation failed: {str(e)}"
                # print 函数输出模板渲染失败的警告信息到控制台
                print(f"Template rendering failed: {e}")
        else:
            # self.body 被设定为默认的邮件内容字符串
            # 当既没有提供直接内容也无法使用模板时的后备方案
            self.body = "This email content is automatically generated by the system."


class MailSender:
    """
    邮件发送器类

    提供发送邮件的核心功能，支持自定义邮件内容和附件。
    """

    def __init__(self):
        """
        初始化邮件发送器

        使用全局邮件配置实例 mail_settings
        """
        # 使用全局配置实例赋值给 self.settings
        self.settings = mail_settings

    def _create_message(self, email_msg: EmailMessage) -> MIMEMultipart:
        """
        创建邮件消息对象

        参数:
            email_msg (EmailMessage): 邮件消息实例

        返回值:
            MIMEMultipart: 构建好的邮件消息对象
        """
        # 创建 MIMEMultipart 对象作为邮件主体
        # 设置邮件的 From、To、Subject 字段
        msg = MIMEMultipart()
        msg['From'] = f"{self.settings.mail_from_name} <{self.settings.mail_from_address}>"
        msg['To'] = ', '.join(email_msg.to)
        msg['Subject'] = email_msg.subject

        # 创建 MIMEText 对象作为邮件正文
        # 根据 content_type 设置内容类型
        body_part = MIMEText(email_msg.body, email_msg.content_type, 'utf-8')
        msg.attach(body_part)

        # 如果有附件，添加附件到邮件中
        for attachment in email_msg.attachments:
            msg.attach(attachment)

        return msg

    async def send_email(self, email_msg: EmailMessage) -> Dict[str, Any]:
        """
        发送邮件

        参数:
            email_msg (EmailMessage): 要发送的邮件消息实例

        返回值:
            Dict[str, Any]: 包含发送结果和详细错误信息的字典
        """
        # datetime.now 函数获取当前时间戳用于错误记录
        from datetime import datetime
        
        try:
            # _create_message 方法通过传入邮件消息实例
            # 创建MIME格式的邮件对象，结果赋值给 msg 变量
            msg = self._create_message(email_msg)

            # aiosmtplib.send 函数通过传入邮件对象和服务器配置
            # 异步发送邮件到SMTP服务器，根据端口选择加密方式
            if self.settings.mail_port == 587:
                # aiosmtplib.send 函数使用STARTTLS加密方式
                # 传入邮件对象、主机名、端口、认证信息和start_tls=True
                await send(
                    msg,
                    hostname=self.settings.mail_host,
                    port=self.settings.mail_port,
                    username=self.settings.mail_username,
                    password=self.settings.mail_password,
                    start_tls=True,
                    timeout=float(self.settings.mail_timeout)
                )
            else:
                # aiosmtplib.send 函数使用直接TLS加密方式
                # 传入邮件对象、主机名、端口、认证信息和use_tls配置
                await send(
                    msg,
                    hostname=self.settings.mail_host,
                    port=self.settings.mail_port,
                    username=self.settings.mail_username,
                    password=self.settings.mail_password,
                    use_tls=True if self.settings.mail_encryption.upper() == 'TLS' else False,
                    timeout=float(self.settings.mail_timeout)
                )

            # len 函数检查邮件是否包含附件，用于成功状态记录
            has_attachments = len(email_msg.attachments) > 0
            
            # 根据是否有附件生成不同的成功信息
            if has_attachments:
                # print 函数输出带附件邮件发送成功的信息
                print(f"Email with {len(email_msg.attachments)} attachments sent successfully to {email_msg.to[0]}")
                attachment_info = f"attachments: {len(email_msg.attachments)}"
            else:
                attachment_info = "no attachments"
            
            # 发送成功时返回包含成功状态和附件信息的结果字典
            return {
                'success': True,
                'recipient': email_msg.to[0] if email_msg.to else 'unknown',
                'timestamp': datetime.now().isoformat(),
                'attachment_info': attachment_info,
                'message': 'Email sent successfully'
            }

        except Exception as e:
            # type 函数通过传入异常对象获取异常类型名称
            error_type = type(e).__name__
            
            # str 函数通过传入异常对象获取详细错误消息
            error_message = str(e)
            
            # datetime.now 函数获取当前时间并格式化为ISO标准时间戳
            error_timestamp = datetime.now().isoformat()
            
            # len 函数检查邮件是否包含附件，用于错误分析
            has_attachments = len(email_msg.attachments) > 0
            
            # 根据是否有附件生成不同的错误提示
            if has_attachments:
                # print 函数输出带附件邮件发送失败的详细信息
                print(f"Email with {len(email_msg.attachments)} attachments failed: {error_type}: {error_message}")
                attachment_info = f"attachments: {len(email_msg.attachments)}"
            else:
                # print 函数输出普通邮件发送失败信息
                print(f"Email sending failed: {error_type}: {error_message}")
                attachment_info = "no attachments"
            
            # 发送失败时返回包含详细错误信息和附件状态的结果字典
            return {
                'success': False,
                'recipient': email_msg.to[0] if email_msg.to else 'unknown',
                'timestamp': error_timestamp,
                'error_type': error_type,
                'error_message': error_message,
                'attachment_info': attachment_info,
                'message': f'Email sending failed: {error_type}'
            }


# 创建全局邮件发送器实例
# 提供给其他模块直接使用
mail_sender = MailSender()


async def send_email(to: Union[str, List[str]],
                    subject: str,
                    body: str,
                    content_type: str = 'plain') -> bool:
    """
    发送邮件的便捷函数（向下兼容接口）

    参数:
        to (Union[str, List[str]]): 收件人邮箱地址
        subject (str): 邮件主题
        body (str): 邮件正文内容
        content_type (str): 内容类型，默认为 'plain'

    返回值:
        bool: 发送成功返回 True，失败返回 False
    """
    # EmailMessage 构造函数通过传入收件人、主题、正文和内容类型
    # 创建邮件消息实例，结果赋值给 email_msg 变量
    email_msg = EmailMessage(
        to=to,
        subject=subject,
        body=body,
        content_type=content_type
    )

    # mail_sender.send_email 方法通过传入邮件消息实例
    # 异步发送邮件，返回详细结果字典，结果赋值给 result 变量
    result = await mail_sender.send_email(email_msg)
    
    # result.get 方法通过传入 'success' 键从结果字典中提取成功标识
    # 返回布尔值保持向下兼容性
    return result.get('success', False)


async def send_template_email(to: Union[str, List[str]],
                             subject: str,
                             template_name: str,
                             template_vars: Dict[str, Any],
                             content_type: str = 'html') -> bool:
    """
    发送模板邮件的便捷函数
    
    使用指定模板和变量生成邮件内容，支持个性化邮件发送。
    
    参数:
        to (Union[str, List[str]]): 收件人邮箱地址
        subject (str): 邮件主题
        template_name (str): 模板名称
        template_vars (Dict[str, Any]): 模板变量字典
        content_type (str): 内容类型，默认为 'html'
        
    返回值:
        bool: 发送成功返回 True，失败返回 False
    """
    # EmailMessage 构造函数通过传入收件人、主题、模板名和变量
    # 创建基于模板的邮件消息实例，结果赋值给 email_msg 变量
    email_msg = EmailMessage(
        to=to,
        subject=subject,
        template_name=template_name,
        template_vars=template_vars,
        content_type=content_type
    )
    
    # mail_sender.send_email 方法通过传入邮件消息实例
    # 异步发送模板邮件，返回详细结果字典，结果赋值给 result 变量
    result = await mail_sender.send_email(email_msg)
    
    # result.get 方法通过传入 'success' 键从结果字典中提取成功标识
    # 返回布尔值保持向下兼容性
    return result.get('success', False)


async def send_bulk_email(recipients: List[str],
                         subject: str,
                         body: str,
                         content_type: str = 'plain',
                         batch_size: int = 10,
                         delay_between_batches: float = 1.0) -> Dict[str, Any]:
    """
    批量发送邮件的便捷函数
    
    将大量收件人分批处理，避免一次性发送过多邮件。
    支持批次间延迟，防止触发邮件服务商的发送限制。
    
    参数:
        recipients (List[str]): 收件人邮箱地址列表
        subject (str): 邮件主题
        body (str): 邮件正文内容
        content_type (str): 内容类型，默认为 'plain'
        batch_size (int): 每批发送数量，默认为 10
        delay_between_batches (float): 批次间延迟秒数，默认为 1.0
        
    返回值:
        Dict[str, Any]: 包含发送统计信息的字典
    """
    # total_recipients 通过 len 函数获取收件人总数
    total_recipients = len(recipients)
    
    # success_count 被初始化为 0，用于统计成功发送的邮件数量
    success_count = 0
    
    # failed_recipients 被初始化为空列表，用于记录发送失败的邮箱
    failed_recipients = []
    
    # batches 通过 range 函数和步长生成批次起始索引列表
    # 用于将收件人列表分割成指定大小的批次
    batches = list(range(0, total_recipients, batch_size))
    
    # for batch_start in batches 遍历每个批次的起始索引
    for batch_index, batch_start in enumerate(batches):
        # batch_end 通过 min 函数计算当前批次的结束索引
        # 确保不会超出收件人列表的范围
        batch_end = min(batch_start + batch_size, total_recipients)
        
        # current_batch 通过切片操作获取当前批次的收件人列表
        current_batch = recipients[batch_start:batch_end]
        
        # print 函数输出当前批次的处理进度信息
        print(f"Processing batch {batch_index + 1}/{len(batches)}: {len(current_batch)} recipients")
        
        # _send_batch 函数通过传入当前批次收件人和邮件参数
        # 异步处理当前批次的邮件发送，返回成功邮箱和失败详情列表
        batch_success, batch_failed_details = await _send_batch(
            current_batch, subject, body, content_type
        )
        
        # success_count 累加当前批次成功发送的数量
        success_count += len(batch_success)
        
        # failed_recipients.extend 方法将当前批次失败的邮箱地址
        # 从详细错误信息中提取并添加到总的失败列表中
        failed_recipients.extend([f['email'] for f in batch_failed_details])
        
        # if 条件检查是否不是最后一个批次且需要延迟
        if batch_index < len(batches) - 1 and delay_between_batches > 0:
            # asyncio.sleep 函数通过传入延迟秒数
            # 异步暂停指定时间，避免发送过快
            await asyncio.sleep(delay_between_batches)
    
    # return 语句返回包含发送统计信息的字典
    return {
        'total_recipients': total_recipients,
        'success_count': success_count,
        'failed_count': len(failed_recipients),
        'failed_recipients': failed_recipients,
        'success_rate': (success_count / total_recipients) * 100 if total_recipients > 0 else 0
    }


async def send_bulk_template_email(recipients: List[Dict[str, Any]],
                                  subject: str,
                                  template_name: str,
                                  content_type: str = 'html',
                                  batch_size: int = 10,
                                  delay_between_batches: float = 1.0) -> Dict[str, Any]:
    """
    批量发送个性化模板邮件的便捷函数
    
    为每个收件人使用不同的模板变量，实现个性化批量邮件发送。
    
    参数:
        recipients (List[Dict[str, Any]]): 收件人信息列表，每个元素包含email和vars字段
        subject (str): 邮件主题
        template_name (str): 模板名称
        content_type (str): 内容类型，默认为 'html'
        batch_size (int): 每批发送数量，默认为 10
        delay_between_batches (float): 批次间延迟秒数，默认为 1.0
        
    返回值:
        Dict[str, Any]: 包含发送统计信息的字典
    """
    # total_recipients 通过 len 函数获取收件人总数
    total_recipients = len(recipients)
    
    # success_count 被初始化为 0，用于统计成功发送的邮件数量
    success_count = 0
    
    # failed_recipients 被初始化为空列表，用于记录发送失败的收件人信息
    failed_recipients = []
    
    # batches 通过 range 函数和步长生成批次起始索引列表
    batches = list(range(0, total_recipients, batch_size))
    
    # for batch_start in batches 遍历每个批次的起始索引
    for batch_index, batch_start in enumerate(batches):
        # batch_end 通过 min 函数计算当前批次的结束索引
        batch_end = min(batch_start + batch_size, total_recipients)
        
        # current_batch 通过切片操作获取当前批次的收件人信息列表
        current_batch = recipients[batch_start:batch_end]
        
        # print 函数输出当前批次的处理进度信息
        print(f"Processing template batch {batch_index + 1}/{len(batches)}: {len(current_batch)} recipients")
        
        # _send_template_batch 函数通过传入当前批次和邮件参数
        # 异步处理当前批次的模板邮件发送，返回成功和失败列表
        batch_success, batch_failed = await _send_template_batch(
            current_batch, subject, template_name, content_type
        )
        
        # success_count 累加当前批次成功发送的数量
        success_count += len(batch_success)
        
        # failed_recipients.extend 方法将当前批次失败的邮箱地址
        # 从详细错误信息中提取并添加到总的失败列表中
        failed_recipients.extend([f['email'] for f in batch_failed])
        
        # if 条件检查是否不是最后一个批次且需要延迟
        if batch_index < len(batches) - 1 and delay_between_batches > 0:
            # asyncio.sleep 函数通过传入延迟秒数异步暂停
            await asyncio.sleep(delay_between_batches)
    
    # return 语句返回包含发送统计信息的字典
    return {
        'total_recipients': total_recipients,
        'success_count': success_count,
        'failed_count': len(failed_recipients),
        'failed_recipients': failed_recipients,
        'success_rate': (success_count / total_recipients) * 100 if total_recipients > 0 else 0
    }


async def _send_batch(recipients: List[str],
                     subject: str,
                     body: str,
                     content_type: str) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    发送单个批次的邮件
    
    并发处理批次内的所有邮件发送，收集详细的错误信息。
    
    参数:
        recipients (List[str]): 当前批次的收件人邮箱列表
        subject (str): 邮件主题
        body (str): 邮件正文
        content_type (str): 内容类型
        
    返回值:
        tuple: (成功发送的邮箱列表, 失败发送的详细信息列表)
    """
    # success_list 被初始化为空列表，用于记录成功发送的邮箱
    success_list = []
    
    # failed_list 被初始化为空列表，用于记录失败发送的详细信息
    failed_list = []
    
    # mail_sender.send_email 方法通过直接调用底层发送器获取详细结果
    # 创建协程任务列表，每个任务返回包含详细信息的字典
    send_tasks = []
    for email in recipients:
        # EmailMessage 构造函数通过传入邮件参数创建邮件消息对象
        email_msg = EmailMessage(to=email, subject=subject, body=body, content_type=content_type)
        
        # mail_sender.send_email 方法作为协程任务添加到任务列表
        send_tasks.append(mail_sender.send_email(email_msg))
    
    # asyncio.gather 函数通过传入所有发送任务和异常处理参数
    # 并发执行所有邮件发送，返回详细结果列表，结果赋值给 results
    results = await asyncio.gather(*send_tasks, return_exceptions=True)
    
    # for i, result in enumerate(results) 遍历发送结果和对应索引
    for i, result in enumerate(results):
        # if 条件检查结果是否为异常对象
        if isinstance(result, Exception):
            # 异常情况下构造详细错误信息字典
            from datetime import datetime
            error_detail = {
                'email': recipients[i],
                'error_type': type(result).__name__,
                'error_message': str(result),
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
            # failed_list.append 方法将错误详情添加到失败列表
            failed_list.append(error_detail)
        # elif 条件检查结果是否为字典且包含success字段
        elif isinstance(result, dict):
            # result.get 方法通过传入 'success' 键检查发送是否成功
            if result.get('success', False):
                # success_list.append 方法将成功邮箱添加到成功列表
                success_list.append(recipients[i])
            else:
                # failed_list.append 方法将失败结果详情添加到失败列表
                failed_list.append(result)
        else:
            # 其他未预期结果的情况下构造默认错误信息
            from datetime import datetime
            error_detail = {
                'email': recipients[i],
                'error_type': 'UnknownError',
                'error_message': f'Unexpected result type: {type(result)}',
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
            # failed_list.append 方法将默认错误详情添加到失败列表
            failed_list.append(error_detail)
    
    # return 语句返回成功邮箱列表和失败详情列表的元组
    return success_list, failed_list


async def _send_template_batch(recipients: List[Dict[str, Any]],
                              subject: str,
                              template_name: str,
                              content_type: str) -> tuple[List[str], List[str]]:
    """
    发送单个批次的模板邮件
    
    为每个收件人使用个性化的模板变量并发发送邮件。
    
    参数:
        recipients (List[Dict[str, Any]]): 当前批次的收件人信息列表
        subject (str): 邮件主题
        template_name (str): 模板名称
        content_type (str): 内容类型
        
    返回值:
        tuple: (成功发送的邮箱列表, 失败发送的邮箱列表)
    """
    # success_list 被初始化为空列表，用于记录成功发送的邮箱
    success_list = []
    
    # failed_list 被初始化为空列表，用于记录失败发送的邮箱
    failed_list = []
    
    # send_tasks 通过列表推导式为每个收件人创建模板邮件发送任务
    # send_template_email 函数作为协程，使用收件人的个性化变量
    send_tasks = [
        send_template_email(
            to=recipient.get('email'),
            subject=subject,
            template_name=template_name,
            template_vars=recipient.get('vars', {}),
            content_type=content_type
        )
        for recipient in recipients
    ]
    
    # asyncio.gather 函数并发执行所有模板邮件发送任务
    # return_exceptions=True 确保异常也会被返回而不是中断执行
    results = await asyncio.gather(*send_tasks, return_exceptions=True)
    
    # for i, result in enumerate(results) 遍历发送结果和对应索引
    for i, result in enumerate(results):
        # recipient_email 通过 get 方法从收件人信息中提取邮箱地址
        recipient_email = recipients[i].get('email', 'unknown')
        
        # if 条件检查结果是否为异常对象
        if isinstance(result, Exception):
            # failed_list.append 方法将发送失败的邮箱添加到失败列表
            failed_list.append(recipient_email)
        # elif 条件检查发送结果是否为True
        elif result is True:
            # success_list.append 方法将发送成功的邮箱添加到成功列表
            success_list.append(recipient_email)
        else:
            # failed_list.append 方法将其他情况的邮箱添加到失败列表
            failed_list.append(recipient_email)
    
    # return 语句返回成功和失败的邮箱列表元组
    return success_list, failed_list


