# 导入标准库模块
import os
from typing import Dict, Any, Optional
from datetime import datetime

# 导入第三方库模块
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateNotFound, TemplateError


class TemplateManager:
    """
    邮件模板管理器类
    
    负责邮件模板的加载、缓存、渲染等核心功能。
    支持HTML和纯文本模板，提供Jinja2模板引擎功能。
    """
    
    def __init__(self):
        """
        初始化模板管理器
        
        设置模板目录路径，配置Jinja2环境，启用模板缓存。
        """
        # os.path.dirname 函数通过传入当前文件绝对路径
        # 获取当前脚本所在目录，结果赋值给 current_dir
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # os.path.join 函数通过传入目录路径和文件夹名
        # 拼接模板目录完整路径，结果赋值给 templates_dir
        templates_dir = os.path.join(current_dir, 'templates')
        
        # self.templates_dir 被设定为模板文件根目录路径
        self.templates_dir = templates_dir
        
        # Environment 构造函数通过传入 FileSystemLoader 实例
        # 和安全配置创建 Jinja2 环境，结果赋值给 self.env
        # enable_async 设为 False，使用同步模板渲染避免事件循环冲突
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml']),
            enable_async=False,
            cache_size=100
        )
        
        # self._setup_globals 方法被调用，用于设置模板全局变量
        self._setup_globals()
        
        # self._template_cache 被初始化为空字典
        # 用于缓存已加载的模板对象，提高性能
        self._template_cache: Dict[str, Template] = {}
    
    def _setup_globals(self):
        """
        设置模板全局变量和过滤器
        
        为所有模板提供通用的全局变量和自定义过滤器。
        """
        # self.env.globals.update 方法通过传入字典
        # 更新模板环境的全局变量，提供 now 函数给所有模板使用
        self.env.globals.update({
            'now': lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        # self.env.filters 字典通过添加 'highlight' 键值对
        # 注册自定义过滤器，用于高亮显示文本
        self.env.filters['highlight'] = self._highlight_filter
    
    def _highlight_filter(self, text: str) -> str:
        """
        高亮过滤器函数
        
        为文本添加HTML高亮标签，用于邮件内容的重点标识。
        
        参数:
            text: 需要高亮的文本字符串
            
        返回值:
            str: 包含高亮HTML标签的文本字符串
        """
        # f-string 格式化通过传入 text 参数
        # 返回包含 highlight 类名的 span 标签包装的文本
        return f'<span class="highlight">{text}</span>'
    
    def get_template(self, template_name: str, content_type: str = 'html') -> Template:
        """
        获取模板对象
        
        根据模板名称和内容类型加载模板，支持缓存机制提高性能。
        
        参数:
            template_name: 模板名称字符串，不包含扩展名
            content_type: 内容类型字符串，'html' 或 'plain'
            
        返回值:
            Template: Jinja2模板对象
            
        异常:
            TemplateNotFound: 当模板文件不存在时抛出
        """
        # _get_template_path 方法通过传入模板名和内容类型
        # 计算完整模板文件路径，结果赋值给 template_path
        template_path = self._get_template_path(template_name, content_type)
        
        # cache_key 通过 f-string 格式化拼接模板名和类型
        # 作为缓存键，用于模板对象的存储和检索
        cache_key = f"{template_name}_{content_type}"
        
        # if 条件判断缓存中是否已存在该模板对象
        if cache_key in self._template_cache:
            # 直接从 self._template_cache 字典返回缓存的模板对象
            return self._template_cache[cache_key]
        
        # try 块开始尝试加载模板文件，捕获可能的异常
        try:
            # self.env.get_template 方法通过传入模板路径
            # 从文件系统加载模板对象，结果赋值给 template
            template = self.env.get_template(template_path)
            
            # self._template_cache 字典通过 cache_key 键
            # 存储加载的模板对象，用于后续快速访问
            self._template_cache[cache_key] = template
            
            # return 语句返回成功加载的模板对象
            return template
            
        # except 捕获 TemplateNotFound 异常
        # 当指定路径的模板文件不存在时触发
        except TemplateNotFound:
            # raise 语句抛出新的 TemplateNotFound 异常
            # 传入包含模板名和类型的错误消息字符串
            raise TemplateNotFound(f"Template not found: {template_name} ({content_type})")
    
    def _get_template_path(self, template_name: str, content_type: str) -> str:
        """
        构建模板文件路径
        
        根据模板名称和内容类型计算相对于模板目录的文件路径。
        
        参数:
            template_name: 模板名称字符串
            content_type: 内容类型字符串
            
        返回值:
            str: 模板文件相对路径
        """
        # if 条件检查内容类型是否为纯文本
        if content_type == 'plain':
            # f-string 格式化通过传入模板名返回纯文本模板路径
            # plain 子目录下的 .txt 扩展名文件
            return f"plain/{template_name}.txt"
        else:
            # f-string 格式化通过传入模板名返回HTML模板路径
            # 根目录下的 .html 扩展名文件
            return f"{template_name}.html"
    
    def render_template(self, 
                       template_name: str, 
                       template_vars: Dict[str, Any], 
                       content_type: str = 'html') -> str:
        """
        渲染模板内容
        
        使用提供的变量渲染指定模板，返回最终的邮件内容。
        
        参数:
            template_name: 模板名称字符串
            template_vars: 模板变量字典
            content_type: 内容类型字符串，默认为 'html'
            
        返回值:
            str: 渲染后的邮件内容字符串
            
        异常:
            TemplateError: 当模板渲染失败时抛出
        """
        # try 块开始尝试渲染模板，捕获可能的异常
        try:
            # get_template 方法通过传入模板名和内容类型
            # 获取模板对象，结果赋值给 template
            template = self.get_template(template_name, content_type)
            
            # template.render 方法通过传入模板变量字典
            # 渲染模板内容，结果赋值给 rendered_content
            rendered_content = template.render(**template_vars)
            
            # return 语句返回渲染完成的内容字符串
            return rendered_content
            
        # except 捕获 TemplateError 及其子类异常
        # 当模板语法错误或渲染失败时触发
        except (TemplateError, Exception) as e:
            # raise 语句抛出新的 TemplateError 异常
            # 传入包含模板名和具体错误信息的消息
            raise TemplateError(f"Template rendering failed for {template_name}: {str(e)}")
    
    def template_exists(self, template_name: str, content_type: str = 'html') -> bool:
        """
        检查模板文件是否存在
        
        验证指定的模板文件在文件系统中是否可用。
        
        参数:
            template_name: 模板名称字符串
            content_type: 内容类型字符串，默认为 'html'
            
        返回值:
            bool: 模板存在返回True，否则返回False
        """
        # _get_template_path 方法通过传入模板名和内容类型
        # 获取模板文件相对路径，结果赋值给 template_path
        template_path = self._get_template_path(template_name, content_type)
        
        # os.path.join 函数通过传入模板目录和相对路径
        # 拼接完整文件路径，结果赋值给 full_path
        full_path = os.path.join(self.templates_dir, template_path)
        
        # os.path.isfile 函数通过传入完整文件路径
        # 检查文件是否存在且为普通文件，返回布尔值
        return os.path.isfile(full_path)
    
    def clear_cache(self):
        """
        清空模板缓存
        
        移除所有已缓存的模板对象，强制重新加载模板文件。
        """
        # self._template_cache.clear 方法被调用
        # 清空字典中的所有缓存模板对象
        self._template_cache.clear()
    
    def get_available_templates(self) -> Dict[str, list]:
        """
        获取可用模板列表
        
        扫描模板目录，返回按内容类型分组的可用模板列表。
        
        返回值:
            Dict[str, list]: 包含html和plain类型模板列表的字典
        """
        # available_templates 被初始化为包含两个空列表的字典
        # 用于分别存储HTML和纯文本模板名称
        available_templates = {
            'html': [],
            'plain': []
        }
        
        # try 块开始尝试扫描模板目录，捕获可能的异常
        try:
            # os.listdir 函数通过传入模板目录路径
            # 获取目录中的所有文件和子目录名，结果赋值给 files
            files = os.listdir(self.templates_dir)
            
            # for filename in files 遍历目录中的每个文件名
            for filename in files:
                # if 条件检查文件名是否以 .html 扩展名结尾
                if filename.endswith('.html'):
                    # filename.replace 方法通过传入扩展名和空字符串
                    # 移除扩展名获取模板名，添加到html列表中
                    template_name = filename.replace('.html', '')
                    available_templates['html'].append(template_name)
            
            # plain_dir 通过 os.path.join 拼接纯文本模板目录路径
            plain_dir = os.path.join(self.templates_dir, 'plain')
            
            # if 条件检查plain子目录是否存在且为目录
            if os.path.isdir(plain_dir):
                # os.listdir 函数扫描plain子目录获取文件列表
                plain_files = os.listdir(plain_dir)
                
                # for filename in plain_files 遍历纯文本模板文件
                for filename in plain_files:
                    # if 条件检查文件名是否以 .txt 扩展名结尾
                    if filename.endswith('.txt'):
                        # filename.replace 方法移除 .txt 扩展名
                        # 获取模板名添加到plain列表中
                        template_name = filename.replace('.txt', '')
                        available_templates['plain'].append(template_name)
                        
        # except 捕获 OSError 异常，文件系统操作失败时触发
        except OSError:
            # pass 语句忽略异常，返回空的模板列表
            pass
        
        # return 语句返回包含可用模板的字典
        return available_templates


# mail_template_manager 全局实例通过 TemplateManager 构造函数创建
# 提供给其他模块直接使用的模板管理器单例
mail_template_manager = TemplateManager()
