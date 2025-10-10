# 导入标准库模块
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, TextIO
from pathlib import Path

# 导入项目内部模块


class BulkMailLogger:
    """
    批量邮件发送日志管理器
    
    负责会话日志记录、断点续传检测和发送状态跟踪。
    提供结构化的批量邮件发送过程记录功能。
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        初始化批量邮件日志管理器
        
        参数:
            log_file: 日志文件路径，如果不指定则自动生成
        """
        # datetime.now 函数获取当前时间用于会话标识生成
        current_time = datetime.now()
        
        # current_time.strftime 方法通过传入时间格式字符串
        # 格式化当前时间为字符串，结果赋值给 time_str 变量
        time_str = current_time.strftime('%Y%m%d_%H%M%S')
        
        # f-string 格式化通过传入时间字符串生成唯一会话ID
        # 结果赋值给 self.session_id 变量
        self.session_id = f"bulk_{time_str}"
        
        # 确定日志文件路径
        if log_file:
            # Path 构造函数通过传入用户指定路径创建路径对象
            # 结果赋值给 self.log_file 变量
            self.log_file = Path(log_file)
        else:
            # os.path.dirname 函数通过传入当前文件路径获取目录
            current_dir = os.path.dirname(__file__)
            
            # os.path.join 函数通过传入目录路径和文件名拼接日志文件路径
            # 结果赋值给 default_log_path 变量
            default_log_path = os.path.join(current_dir, 'logs', f'{self.session_id}.log')
            
            # Path 构造函数通过传入默认路径创建路径对象
            self.log_file = Path(default_log_path)
        
        # self.log_file.parent.mkdir 方法通过传入parents=True和exist_ok=True
        # 创建日志文件的父目录，确保目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # self._log_handle 被初始化为None，用于存储日志文件句柄
        self._log_handle: Optional[TextIO] = None
        
        # self._session_started 被初始化为False，标识会话是否已开始
        self._session_started = False
    
    def start_session(self, email_file: str, template_name: str, total_emails: int, subject: str):
        """
        开始新的邮件发送会话
        
        记录会话开始标记和基本信息到日志文件。
        
        参数:
            email_file: 邮箱文件路径
            template_name: 使用的模板名称
            total_emails: 邮箱总数
            subject: 邮件主题
        """
        # open 函数通过传入日志文件路径和追加模式打开日志文件
        # 指定UTF-8编码，结果赋值给 self._log_handle 变量
        self._log_handle = open(self.log_file, 'a', encoding='utf-8')
        
        # datetime.now 函数获取当前时间并格式化为ISO标准时间戳
        timestamp = datetime.now().isoformat()
        
        # _write_log 方法通过传入会话开始标记和相关信息
        # 写入日志文件，标识新会话的开始
        self._write_log(f"[SESSION_START] {timestamp} | "
                       f"SessionID: {self.session_id} | "
                       f"EmailFile: {email_file} | "
                       f"Template: {template_name} | "
                       f"Subject: {subject} | "
                       f"Total: {total_emails}")
        
        # self._session_started 被设定为True，标识会话已开始
        self._session_started = True
    
    def log_email_result(self, email: str, success: bool, error_details: Optional[Dict[str, Any]] = None):
        """
        记录单个邮件的发送结果
        
        参数:
            email: 收件人邮箱地址
            success: 发送是否成功
            error_details: 错误详情字典（失败时提供）
        """
        # datetime.now 函数获取当前时间并格式化为ISO标准时间戳
        timestamp = datetime.now().isoformat()
        
        if success:
            # _write_log 方法通过传入进度标记和成功信息
            # 记录邮件发送成功的日志条目
            self._write_log(f"[PROGRESS] {email} | SUCCESS | {timestamp}")
        else:
            # error_details.get 方法通过传入键名从错误详情中提取信息
            # 如果错误详情不存在则使用默认值
            error_type = error_details.get('error_type', 'Unknown') if error_details else 'Unknown'
            error_message = error_details.get('error_message', 'No details') if error_details else 'No details'
            
            # _write_log 方法通过传入进度标记和失败信息
            # 记录邮件发送失败的详细日志条目
            self._write_log(f"[PROGRESS] {email} | FAILED | "
                           f"{error_type}: {error_message} | {timestamp}")
    
    def log_batch_complete(self, batch_index: int, total_batches: int, 
                          batch_success: int, batch_total: int):
        """
        记录批次完成信息
        
        参数:
            batch_index: 当前批次索引（从1开始）
            total_batches: 总批次数
            batch_success: 当前批次成功数量
            batch_total: 当前批次总数量
        """
        # datetime.now 函数获取当前时间并格式化为ISO标准时间戳
        timestamp = datetime.now().isoformat()
        
        # _write_log 方法通过传入批次标记和统计信息
        # 记录批次完成的日志条目
        self._write_log(f"[BATCH] Batch {batch_index}/{total_batches} completed | "
                       f"Success: {batch_success}/{batch_total} | {timestamp}")
    
    def end_session(self, total_count: int, success_count: int, failed_count: int, status: str = "COMPLETED"):
        """
        结束邮件发送会话
        
        记录会话结束标记和最终统计信息。
        
        参数:
            total_count: 邮件总数
            success_count: 成功发送数量
            failed_count: 失败发送数量
            status: 会话结束状态（COMPLETED/INTERRUPTED/FAILED）
        """
        # datetime.now 函数获取当前时间并格式化为ISO标准时间戳
        timestamp = datetime.now().isoformat()
        
        # success_rate 通过计算成功数量除以总数量乘以100得到成功率
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        # _write_log 方法通过传入会话结束标记和统计信息
        # 记录会话结束的日志条目
        self._write_log(f"[SESSION_END] {timestamp} | "
                       f"SessionID: {self.session_id} | "
                       f"Status: {status} | "
                       f"Success: {success_count}/{total_count} | "
                       f"Failed: {failed_count} | "
                       f"Rate: {success_rate:.1f}%")
        
        # 关闭日志文件句柄
        if self._log_handle:
            # self._log_handle.close 方法关闭日志文件
            self._log_handle.close()
            # self._log_handle 被设定为None，释放文件句柄
            self._log_handle = None
        
        # self._session_started 被设定为False，标识会话已结束
        self._session_started = False
    
    def _write_log(self, message: str):
        """
        写入日志消息到文件
        
        参数:
            message: 要写入的日志消息
        """
        if self._log_handle:
            # self._log_handle.write 方法通过传入消息和换行符
            # 将日志内容写入文件
            self._log_handle.write(f"{message}\n")
            
            # self._log_handle.flush 方法立即刷新文件缓冲区
            # 确保日志内容及时写入磁盘
            self._log_handle.flush()
    
    @staticmethod
    def detect_incomplete_sessions(logs_dir: str = None) -> List[Dict[str, Any]]:
        """
        检测未完成的邮件发送会话
        
        扫描日志目录，查找有SESSION_START但没有SESSION_END的会话。
        
        参数:
            logs_dir: 日志目录路径，如果不指定则使用默认目录
            
        返回值:
            List[Dict[str, Any]]: 未完成会话的信息列表
        """
        if not logs_dir:
            # os.path.dirname 函数获取当前文件所在目录
            current_dir = os.path.dirname(__file__)
            
            # os.path.join 函数通过传入目录路径和logs文件夹名
            # 拼接日志目录完整路径，结果赋值给 logs_dir 变量
            logs_dir = os.path.join(current_dir, 'logs')
        
        # Path 构造函数通过传入日志目录路径创建路径对象
        logs_path = Path(logs_dir)
        
        # logs_path.exists 方法检查日志目录是否存在
        if not logs_path.exists():
            # 日志目录不存在时返回空列表
            return []
        
        # incomplete_sessions 被初始化为空列表，用于存储未完成会话信息
        incomplete_sessions = []
        
        # logs_path.glob 方法通过传入'*.log'模式
        # 获取目录中所有.log文件的生成器对象
        for log_file in logs_path.glob('*.log'):
            # _analyze_log_file 方法通过传入日志文件路径
            # 分析日志文件的会话状态，返回会话信息字典或None
            session_info = BulkMailLogger._analyze_log_file(log_file)
            
            # if 条件检查会话信息是否存在且为未完成状态
            if session_info and not session_info['completed']:
                # incomplete_sessions.append 方法将未完成会话信息添加到列表
                incomplete_sessions.append(session_info)
        
        # return 语句返回所有未完成会话信息的列表
        return incomplete_sessions
    
    @staticmethod
    def _analyze_log_file(log_file: Path) -> Optional[Dict[str, Any]]:
        """
        分析单个日志文件的会话状态
        
        解析日志文件内容，提取会话信息和完成状态。
        
        参数:
            log_file: 日志文件路径对象
            
        返回值:
            Optional[Dict[str, Any]]: 会话信息字典，如果无法解析则返回None
        """
        # session_info 被初始化为包含基本信息的字典
        session_info = {
            'log_file': str(log_file),
            'session_id': None,
            'email_file': None,
            'template': None,
            'subject': None,
            'total_emails': 0,
            'completed': False,
            'sent_emails': [],
            'start_time': None,
            'end_time': None
        }
        
        try:
            # open 函数通过传入日志文件路径和只读模式打开文件
            # 指定UTF-8编码，结果赋值给 f 变量
            with open(log_file, 'r', encoding='utf-8') as f:
                # f.readlines 方法读取文件所有行，结果赋值给 lines 变量
                lines = f.readlines()
            
            # for line in lines 遍历日志文件的每一行
            for line in lines:
                # line.strip 方法移除行首尾的空白字符
                line = line.strip()
                
                # if 条件检查行是否以SESSION_START标记开始
                if line.startswith('[SESSION_START]'):
                    # _parse_session_start 方法通过传入日志行内容
                    # 解析会话开始信息，更新session_info字典
                    BulkMailLogger._parse_session_start(line, session_info)
                
                # elif 条件检查行是否以PROGRESS标记开始
                elif line.startswith('[PROGRESS]'):
                    # _parse_progress_line 方法通过传入日志行内容
                    # 解析邮件发送进度，更新已发送邮件列表
                    BulkMailLogger._parse_progress_line(line, session_info)
                
                # elif 条件检查行是否以SESSION_END标记开始
                elif line.startswith('[SESSION_END]'):
                    # session_info 字典的 'completed' 键被设定为True
                    # 标识会话已完成
                    session_info['completed'] = True
                    
                    # _parse_session_end 方法通过传入日志行内容
                    # 解析会话结束时间信息
                    BulkMailLogger._parse_session_end(line, session_info)
            
            # return 语句返回解析完成的会话信息字典
            return session_info
            
        except Exception as e:
            # print 函数输出日志文件分析失败的错误信息
            print(f"Failed to analyze log file {log_file}: {e}")
            
            # 分析失败时返回None
            return None
    
    @staticmethod
    def _parse_session_start(line: str, session_info: Dict[str, Any]):
        """
        解析会话开始日志行
        
        从SESSION_START日志行中提取会话基本信息。
        
        参数:
            line: 日志行内容
            session_info: 要更新的会话信息字典
        """
        # line.split 方法通过传入' | '分隔符将日志行分割成部分
        parts = line.split(' | ')
        
        # for part in parts 遍历日志行的每个部分
        for part in parts:
            # part.strip 方法移除部分内容的首尾空白
            part = part.strip()
            
            # if 条件检查部分是否以SessionID:开头
            if part.startswith('SessionID:'):
                # part.split 方法通过传入':'分隔符获取会话ID值
                # [1].strip 获取冒号后的内容并移除空白
                session_info['session_id'] = part.split(':', 1)[1].strip()
            
            # elif 条件检查部分是否以EmailFile:开头
            elif part.startswith('EmailFile:'):
                # part.split 方法获取邮箱文件路径
                session_info['email_file'] = part.split(':', 1)[1].strip()
            
            # elif 条件检查部分是否以Template:开头
            elif part.startswith('Template:'):
                # part.split 方法获取模板名称
                session_info['template'] = part.split(':', 1)[1].strip()
            
            # elif 条件检查部分是否以Subject:开头
            elif part.startswith('Subject:'):
                # part.split 方法获取邮件主题
                session_info['subject'] = part.split(':', 1)[1].strip()
            
            # elif 条件检查部分是否以Total:开头
            elif part.startswith('Total:'):
                # int 函数通过传入冒号后的数字字符串转换为整数
                session_info['total_emails'] = int(part.split(':', 1)[1].strip())
        
        # parts[0].split 方法通过传入']'分隔符获取时间戳部分
        # [1].strip 获取右括号后的时间戳内容
        if len(parts) > 0 and ']' in parts[0]:
            time_part = parts[0].split(']', 1)[1].strip()
            # session_info 字典的 'start_time' 键被赋值为提取的时间戳
            session_info['start_time'] = time_part
    
    @staticmethod
    def _parse_progress_line(line: str, session_info: Dict[str, Any]):
        """
        解析邮件发送进度日志行
        
        从PROGRESS日志行中提取已发送的邮箱地址。
        
        参数:
            line: 日志行内容
            session_info: 要更新的会话信息字典
        """
        # line.split 方法通过传入' | '分隔符分割进度日志行
        parts = line.split(' | ')
        
        # len 函数检查分割后的部分数量是否足够
        if len(parts) >= 3:
            # parts[1].strip 方法获取邮箱地址部分并移除空白
            email = parts[1].strip()
            
            # parts[2].strip 方法获取发送状态并移除空白
            status = parts[2].strip()
            
            # if 条件检查发送状态是否为SUCCESS
            if status == 'SUCCESS':
                # session_info['sent_emails'].append 方法将成功发送的邮箱
                # 添加到已发送邮件列表中
                session_info['sent_emails'].append(email)
    
    @staticmethod
    def _parse_session_end(line: str, session_info: Dict[str, Any]):
        """
        解析会话结束日志行
        
        从SESSION_END日志行中提取会话结束时间。
        
        参数:
            line: 日志行内容
            session_info: 要更新的会话信息字典
        """
        # line.split 方法通过传入']'分隔符获取时间戳部分
        if ']' in line:
            # line.split 方法获取右括号后的时间戳内容
            time_part = line.split(']', 1)[1].split(' | ')[0].strip()
            
            # session_info 字典的 'end_time' 键被赋值为提取的结束时间
            session_info['end_time'] = time_part
    
    def get_remaining_emails(self, all_emails: List[str]) -> List[str]:
        """
        获取未发送的邮箱地址列表
        
        通过对比总邮箱列表和已发送列表，计算剩余未发送的邮箱。
        
        参数:
            all_emails: 完整的邮箱地址列表
            
        返回值:
            List[str]: 未发送的邮箱地址列表
        """
        # set 构造函数通过传入已发送邮件列表创建集合
        # 用于快速查找和去重，结果赋值给 sent_set 变量
        sent_set = set(self._get_sent_emails_from_current_log())
        
        # 列表推导式通过遍历所有邮箱地址
        # 筛选出不在已发送集合中的邮箱，返回未发送列表
        return [email for email in all_emails if email not in sent_set]
    
    def _get_sent_emails_from_current_log(self) -> List[str]:
        """
        从当前日志文件读取已发送的邮箱地址
        
        返回值:
            List[str]: 已发送成功的邮箱地址列表
        """
        # sent_emails 被初始化为空列表，用于存储已发送邮箱
        sent_emails = []
        
        try:
            # open 函数通过传入日志文件路径和只读模式打开文件
            with open(self.log_file, 'r', encoding='utf-8') as f:
                # f.readlines 方法读取所有日志行，结果赋值给 lines 变量
                lines = f.readlines()
            
            # for line in lines 遍历每一行日志内容
            for line in lines:
                # line.strip 方法移除行首尾空白字符
                line = line.strip()
                
                # if 条件检查是否为成功发送的进度日志行
                if line.startswith('[PROGRESS]') and ' | SUCCESS | ' in line:
                    # line.split 方法通过传入' | '分隔符分割日志行
                    parts = line.split(' | ')
                    
                    # len 函数检查分割部分数量是否足够
                    if len(parts) >= 2:
                        # parts[1].strip 方法获取邮箱地址并移除空白
                        email = parts[1].strip()
                        
                        # sent_emails.append 方法将邮箱添加到已发送列表
                        sent_emails.append(email)
                        
        except Exception as e:
            # print 函数输出读取日志文件失败的错误信息
            print(f"Failed to read sent emails from log: {e}")
        
        # return 语句返回已发送邮箱列表
        return sent_emails
    
    def close(self):
        """
        关闭日志管理器
        
        确保日志文件句柄正确关闭，释放系统资源。
        """
        if self._log_handle:
            # self._log_handle.close 方法关闭日志文件句柄
            self._log_handle.close()
            
            # self._log_handle 被设定为None，释放句柄引用
            self._log_handle = None
