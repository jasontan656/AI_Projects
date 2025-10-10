# 导入标准库模块
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# 导入项目内部模块
from .BulkMailLogger import BulkMailLogger


class SessionManager:
    """Mail sending session manager.

    Handles session state detection, resume logic, and task orchestration.
    Provides recovery for incomplete tasks and scheduling for new tasks.
    """
    
    def __init__(self, logs_dir: Optional[str] = None):
        """Initialize the session manager.

        Args:
            logs_dir: Logs directory path. Uses default path if not provided.
        """
        if not logs_dir:
            # os.path.dirname 函数获取当前文件所在目录
            current_dir = os.path.dirname(__file__)
            
            # os.path.join 函数通过传入目录路径和logs文件夹名
            # 拼接默认日志目录路径，结果赋值给 self.logs_dir 变量
            self.logs_dir = os.path.join(current_dir, 'logs')
        else:
            # logs_dir 参数直接赋值给 self.logs_dir 变量
            self.logs_dir = logs_dir
        
        # Path 构造函数通过传入日志目录路径创建路径对象
        # 结果赋值给 self.logs_path 变量
        self.logs_path = Path(self.logs_dir)
        
        # self.logs_path.mkdir 方法通过传入parents=True和exist_ok=True
        # 创建日志目录，确保目录存在
        self.logs_path.mkdir(parents=True, exist_ok=True)
    
    def detect_incomplete_sessions(self) -> List[Dict[str, Any]]:
        """Detect all incomplete mail sending sessions from the logs directory."""
        # BulkMailLogger.detect_incomplete_sessions 静态方法通过传入日志目录
        # 扫描并分析所有日志文件，返回未完成会话列表
        return BulkMailLogger.detect_incomplete_sessions(self.logs_dir)
    
    def ask_user_resume_choice(self, incomplete_sessions: List[Dict[str, Any]]) -> str:
        """Interactively ask whether to resume incomplete tasks.

        Returns one of: 'resume', 'skip', 'cancel'.
        """
        if not incomplete_sessions:
            # 没有未完成会话时返回skip
            return 'skip'
        
        # print 函数输出检测到的未完成任务数量
        print(f"\nRESUME_DETECT: Found {len(incomplete_sessions)} incomplete email tasks:")
        
        # for i, session in enumerate(incomplete_sessions) 遍历未完成会话
        for i, session in enumerate(incomplete_sessions, 1):
            # len 函数计算剩余未发送的邮件数量
            remaining_count = session['total_emails'] - len(session['sent_emails'])
            
            # Display each incomplete session details (ASCII only)
            print(
                f"  {i}. Template: {session['template']} | "
                f"Email file: {session['email_file']} | "
                f"Remaining: {remaining_count}/{session['total_emails']} | "
                f"Start time: {session['start_time']}"
            )
        
        print("\nPlease choose:")
        print("  r) Resume and complete all incomplete tasks")
        print("  s) Skip incomplete tasks and start a new task")
        print("  c) Cancel")
        
        # input 函数提示用户输入选择并获取用户输入
        while True:
            # input 函数获取用户输入并转换为小写字母
            choice = input("\nEnter choice (r/s/c): ").lower().strip()
            
            # if 条件检查用户输入是否为有效选项
            if choice in ['r', 'resume']:
                return 'resume'
            elif choice in ['s', 'skip']:
                return 'skip' 
            elif choice in ['c', 'cancel']:
                return 'cancel'
            else:
                print("WARN: Please enter a valid option (r/s/c)")
    
    def validate_template_exists(self, template_name: str) -> bool:
        """Return True if the specified template exists in the filesystem."""
        try:
            # 导入模板管理器
            from .TemplateManager import mail_template_manager
            
            # mail_template_manager.template_exists 方法通过传入模板名和html类型
            # 检查模板文件是否存在，返回布尔值
            return mail_template_manager.template_exists(template_name, 'html')
            
        except ImportError:
            # 模板管理器不可用时返回False
            return False
    
    def load_email_file(self, email_file: str) -> List[str]:
        """Load email addresses from a file (plain list or CSV-like lines).

        Raises FileNotFoundError or ValueError on errors.
        """
        # Path 构造函数通过传入邮箱文件路径创建路径对象
        file_path = Path(email_file)
        
        # file_path.exists 方法检查文件是否存在
        if not file_path.exists():
            raise FileNotFoundError(f"Email file not found: {email_file}")
        
        # emails 被初始化为空列表，用于存储提取的邮箱地址
        emails = []
        
        try:
            # open 函数通过传入文件路径和只读模式打开邮箱文件
            # 指定UTF-8编码，结果赋值给 f 变量
            with open(file_path, 'r', encoding='utf-8') as f:
                # f.readlines 方法读取文件所有行，结果赋值给 lines 变量
                lines = f.readlines()
            
            # for line in lines 遍历文件的每一行
            for line in lines:
                # line.strip 方法移除行首尾的空白字符，结果赋值给 line 变量
                line = line.strip()
                
                # if 条件检查行是否非空且包含@符号（邮箱格式基本验证）
                if line and '@' in line:
                    # _extract_email_from_line 方法通过传入行内容
                    # 提取邮箱地址，结果赋值给 email 变量
                    email = self._extract_email_from_line(line)
                    
                    # if 条件检查提取的邮箱是否有效
                    if email:
                        # emails.append 方法将有效邮箱添加到邮箱列表
                        emails.append(email)
            
            # len 函数检查提取的邮箱数量是否为0
            if len(emails) == 0:
                raise ValueError(f"No valid email addresses found in file: {email_file}")
            
            # return 语句返回提取的邮箱地址列表
            return emails
            
        except UnicodeDecodeError:
            raise ValueError(f"File encoding error; ensure UTF-8: {email_file}")
    
    def _extract_email_from_line(self, line: str) -> Optional[str]:
        """Extract an email address from a single line of text."""
        # line.strip 方法移除行首尾空白字符
        line = line.strip()
        
        # if 条件检查行是否为空或以#开头（注释行）
        if not line or line.startswith('#'):
            return None
        
        # ',' in line 检查行是否包含逗号（CSV格式）
        if ',' in line:
            # line.split 方法通过传入','分隔符分割CSV行
            parts = line.split(',')
            
            # for part in parts 遍历分割后的每个部分
            for part in parts:
                # part.strip 方法移除部分内容的空白字符
                part = part.strip()
                
                # '@' in part and '.' in part 检查部分是否像邮箱地址
                if '@' in part and '.' in part:
                    # return 语句返回找到的邮箱地址
                    return part
        else:
            # '@' in line and '.' in line 检查整行是否为邮箱地址格式
            if '@' in line and '.' in line:
                # return 语句返回整行作为邮箱地址
                return line
        
        # 无法识别有效邮箱时返回None
        return None
    
    def get_resume_plan(self, incomplete_sessions: List[Dict[str, Any]], 
                       new_task: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Compute resume plan and pending new task from inputs."""
        # resume_sessions 被初始化为空列表，用于存储需要恢复的会话
        resume_sessions = []
        
        # for session in incomplete_sessions 遍历所有未完成会话
        for session in incomplete_sessions:
            # validate_template_exists 方法通过传入会话的模板名称
            # 检查模板是否仍然存在，结果赋值给 template_valid 变量
            template_valid = self.validate_template_exists(session['template'])
            
            # if 条件检查模板是否仍然有效
            if template_valid:
                # resume_sessions.append 方法将有效会话添加到恢复列表
                resume_sessions.append(session)
            else:
                # print 函数输出模板不存在的警告信息
                print(f"WARN: Template for session {session['session_id']} not found: '{session['template']}', skipping")
        
        # 检查新任务是否与恢复任务冲突
        # new_task 变量直接作为新任务信息传递
        pending_new_task = new_task if resume_sessions else new_task
        
        # return 语句返回需要恢复的会话列表和新任务信息的元组
        return resume_sessions, pending_new_task
    
    def calculate_remaining_emails(self, session: Dict[str, Any], all_emails: List[str]) -> List[str]:
        """Calculate remaining (unsent) emails for a session."""
        # set 构造函数通过传入会话的已发送邮件列表创建集合
        # 用于快速查找，结果赋值给 sent_set 变量
        sent_set = set(session.get('sent_emails', []))
        
        # 列表推导式通过遍历所有邮箱地址
        # 筛选出不在已发送集合中的邮箱，返回剩余邮箱列表
        remaining_emails = [email for email in all_emails if email not in sent_set]
        
        # return 语句返回计算出的剩余邮箱列表
        return remaining_emails
    
    def compare_tasks(self, session_task: Dict[str, Any], new_task: Dict[str, Any]) -> bool:
        """Return True if template and subject match between tasks."""
        # session_task.get 方法通过传入'template'键获取会话模板名
        session_template = session_task.get('template', '')
        
        # new_task.get 方法通过传入'template'键获取新任务模板名
        new_template = new_task.get('template', '')
        
        # session_task.get 方法通过传入'subject'键获取会话主题
        session_subject = session_task.get('subject', '')
        
        # new_task.get 方法通过传入'subject'键获取新任务主题
        new_subject = new_task.get('subject', '')
        
        # return 语句通过比较模板名和主题是否都相同返回布尔值
        return (session_template == new_template and 
                session_subject == new_subject)
    
    def should_merge_with_existing(self, incomplete_sessions: List[Dict[str, Any]], 
                                  new_task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return a mergeable session if the new task matches one; else None."""
        # for session in incomplete_sessions 遍历所有未完成会话
        for session in incomplete_sessions:
            # compare_tasks 方法通过传入会话任务和新任务信息
            # 比较任务是否相同，结果赋值给 tasks_match 变量
            tasks_match = self.compare_tasks(session, new_task)
            
            # if 条件检查任务是否匹配
            if tasks_match:
                # return 语句返回匹配的会话信息，可以合并执行
                return session
        
        # 没有找到可合并的会话时返回None
        return None
    
    def create_resume_logger(self, session: Dict[str, Any]) -> BulkMailLogger:
        """Create a logger bound to the existing session log file."""
        # session.get 方法通过传入'log_file'键获取会话的日志文件路径
        log_file = session.get('log_file')
        
        # BulkMailLogger 构造函数通过传入现有日志文件路径
        # 创建日志管理器实例，结果赋值给 logger 变量
        logger = BulkMailLogger(log_file)
        
        # logger.session_id 被设定为会话的原始ID，保持连续性
        logger.session_id = session.get('session_id', logger.session_id)
        
        # return 语句返回配置好的日志管理器实例
        return logger
    
    def clean_old_logs(self, keep_days: int = 7):
        """Delete log files older than keep_days (default 7)."""
        from datetime import datetime, timedelta
        
        # datetime.now 函数获取当前时间
        now = datetime.now()
        
        # timedelta 构造函数通过传入天数创建时间差对象
        cutoff_time = now - timedelta(days=keep_days)
        
        # self.logs_path.glob 方法通过传入'*.log'模式
        # 获取日志目录中所有.log文件的迭代器
        for log_file in self.logs_path.glob('*.log'):
            try:
                # log_file.stat 方法获取文件统计信息
                file_stat = log_file.stat()
                
                # datetime.fromtimestamp 函数通过传入文件修改时间戳
                # 转换为datetime对象，结果赋值给 file_time 变量
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                
                # if 条件检查文件时间是否早于截止时间
                if file_time < cutoff_time:
                    # log_file.unlink 方法删除过期的日志文件
                    log_file.unlink()
                    
                    # print 函数输出删除旧日志文件的信息
                    print(f"LOG_CLEANUP: Deleted old log file: {log_file.name}")
                    
            except Exception as e:
                # print 函数输出删除文件失败的错误信息
                print(f"WARN: Failed to delete log file {log_file.name}: {e}")
    
    def get_session_summary(self, session: Dict[str, Any]) -> str:
        """Return a short human-readable summary of the session."""
        # len 函数计算已发送邮件数量
        sent_count = len(session.get('sent_emails', []))
        
        # session.get 方法获取邮件总数
        total_count = session.get('total_emails', 0)
        
        # 计算剩余未发送邮件数量
        remaining = total_count - sent_count
        
        # f-string 格式化生成会话摘要字符串
        summary = (f"SessionID: {session.get('session_id', 'unknown')} | "
                  f"Template: {session.get('template', 'unknown')} | "
                  f"Progress: {sent_count}/{total_count} | "
                  f"Remaining: {remaining}")
        
        # return 语句返回生成的摘要字符串
        return summary
