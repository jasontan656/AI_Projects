#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bulk mail sending CLI tool

Features:
- Send template-based emails in bulk
- Resume interrupted sessions
- Detailed logging and progress

Usage examples:
    python BulkMail.py emails.txt verification --subject "Your Verification Code"
    python BulkMail.py users.txt welcome --subject "Welcome" --batch-size 20
"""

import os
import sys
import argparse
import asyncio
import signal
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# sys.path.append 通过传入项目根目录路径
# 将项目路径添加到Python模块搜索路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    # 导入邮件发送核心功能
    from shared_utilities.mail import send_bulk_template_email, send_bulk_email
    
    # 导入日志和会话管理功能
    from shared_utilities.mail.BulkMailLogger import BulkMailLogger
    from shared_utilities.mail.SessionManager import SessionManager
    
    print("Mail system modules imported successfully")
    
except ImportError as e:
    print(f"Module import failed: {e}")
    print("Please run this script from the correct project directory")
    sys.exit(1)


class BulkMailSender:
    """Main bulk mail sender class.

    Coordinates logging, session management, and mail sending workflow.
    """
    
    def __init__(self):
        """Initialize the bulk mail sender."""
        # SessionManager 构造函数创建会话管理器实例
        # 结果赋值给 self.session_manager 变量
        self.session_manager = SessionManager()
        
        # self.logger 被初始化为None，在会话开始时创建
        self.logger: Optional[BulkMailLogger] = None
        
        # self.interrupted 被初始化为False，用于标识是否被中断
        self.interrupted = False
        
        # _setup_signal_handlers 方法被调用，设置信号处理器
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Register signal handlers for graceful interruption (SIGINT/SIGTERM)."""
        # signal.signal 函数通过传入SIGINT信号和处理函数
        # 注册中断信号处理器，处理CTRL+C操作
        signal.signal(signal.SIGINT, self._handle_interrupt)
        
        # signal.signal 函数通过传入SIGTERM信号和处理函数
        # 注册终止信号处理器，处理系统终止操作
        signal.signal(signal.SIGTERM, self._handle_interrupt)
    
    def _handle_interrupt(self, signum, frame):
        """Handle interrupt signals and gracefully end the current session."""
        print("\n\nInterrupt signal detected. Stopping safely...")
        
        # self.interrupted 被设定为True，标识发送过程被中断
        self.interrupted = True
        
        # if 条件检查日志管理器是否存在且会话已开始
        if self.logger and self.logger._session_started:
            # logger.end_session 方法通过传入统计信息和中断状态
            # 记录会话被中断结束的日志
            self.logger.end_session(0, 0, 0, "INTERRUPTED")
        
        print("Session saved. You can resume later.")
        
        # sys.exit 函数通过传入退出码0正常退出程序
        sys.exit(0)
    
    async def process_args(self, args) -> int:
        """Process CLI arguments and execute mail sending. Returns exit code (0/1)."""
        try:
            # 1. 检测未完成会话
            print("Checking incomplete email sending sessions...")
            
            # session_manager.detect_incomplete_sessions 方法
            # 扫描日志目录获取未完成会话列表
            incomplete_sessions = self.session_manager.detect_incomplete_sessions()
            
            # 2. 处理附件扫描和参数优化
            # _process_attachments 方法通过传入命令行参数
            # 处理附件文件夹扫描和发送参数优化，返回优化后的参数
            optimized_params = self._process_attachments(args)
            
            # 3. 构建新任务信息
            # 创建新任务信息字典，包含优化后的参数
            new_task = {
                'email_file': args.email_file,
                'template': args.template,
                'subject': args.subject,
                'batch_size': optimized_params['batch_size'],
                'delay': optimized_params['delay'],
                'attachments_dir': args.attachments_dir
            }
            
            # 3. 用户交互：选择处理方式
            if incomplete_sessions:
                # session_manager.ask_user_resume_choice 方法通过传入未完成会话
                # 交互式询问用户选择，返回用户决策字符串
                user_choice = self.session_manager.ask_user_resume_choice(incomplete_sessions)
                
                # if 条件检查用户是否选择取消操作
                if user_choice == 'cancel':
                    print("Operation cancelled")
                    return 0
                elif user_choice == 'resume':
                    # _handle_resume_sessions 方法通过传入未完成会话列表
                    # 处理恢复会话的执行逻辑
                    await self._handle_resume_sessions(incomplete_sessions)
                    
                    # 检查是否还有新任务需要执行
                    # _should_execute_new_task 方法检查是否需要执行新任务
                    if self._should_execute_new_task(incomplete_sessions, new_task):
                        print("\nContinue with new task...")
                        # _execute_new_task 方法执行新的邮件发送任务
                        await self._execute_new_task(args)
                else:
                    # user_choice == 'skip' 时直接执行新任务
                    print("Skipping incomplete tasks, starting new task")
                    # _execute_new_task 方法执行新的邮件发送任务
                    await self._execute_new_task(args)
            else:
                # 没有未完成会话时直接执行新任务
                print("No incomplete sessions found, starting new task")
                # _execute_new_task 方法执行新的邮件发送任务
                await self._execute_new_task(args)
            
            print("\nAll email sending tasks completed!")
            return 0
            
        except Exception as e:
            print(f"Error during processing: {e}")
            return 1
    
    async def _handle_resume_sessions(self, incomplete_sessions: List[Dict[str, Any]]):
        """Resume all incomplete sessions in sequence."""
        # for session in incomplete_sessions 遍历所有未完成会话
        for session in incomplete_sessions:
            print(f"\nResuming session: {session['session_id']}")
            
            # session_manager.get_session_summary 方法通过传入会话信息
            # 生成会话摘要字符串，结果赋值给 summary 变量
            summary = self.session_manager.get_session_summary(session)
            print(f"{summary}")
            
            # _resume_single_session 方法通过传入会话信息
            # 异步恢复单个会话的发送任务
            await self._resume_single_session(session)
    
    async def _resume_single_session(self, session: Dict[str, Any]):
        """Resume a single session by sending remaining emails."""
        try:
            # session_manager.create_resume_logger 方法通过传入会话信息
            # 创建用于恢复的日志管理器，结果赋值给 self.logger 变量
            self.logger = self.session_manager.create_resume_logger(session)
            
            # session_manager.load_email_file 方法通过传入邮件文件路径
            # 加载完整的邮箱地址列表，结果赋值给 all_emails 变量
            all_emails = self.session_manager.load_email_file(session['email_file'])
            
            # session_manager.calculate_remaining_emails 方法通过传入会话信息和邮箱列表
            # 计算剩余未发送的邮箱地址，结果赋值给 remaining_emails 变量
            remaining_emails = self.session_manager.calculate_remaining_emails(session, all_emails)
            
            # len 函数计算剩余邮件数量
            remaining_count = len(remaining_emails)
            
            # if 条件检查是否还有剩余邮件需要发送
            if remaining_count > 0:
                print(f"Continuing to send remaining {remaining_count} emails")
                
                # _send_emails_with_progress 方法通过传入邮件列表和会话参数
                # 执行带进度显示的邮件发送过程，恢复时不处理附件
                await self._send_emails_with_progress(
                    remaining_emails,
                    session['subject'],
                    session['template'],
                    batch_size=20,  # 恢复时使用默认批次大小
                    delay=2.0,      # 恢复时使用默认延迟
                    attachments_dir=None  # 恢复时不处理附件
                )
            else:
                print("Session already completed; no need to resume")
                
        except Exception as e:
            print(f"Failed to resume session: {e}")
            
            # if 条件检查日志管理器是否存在
            if self.logger:
                # logger.end_session 方法记录会话恢复失败
                self.logger.end_session(0, 0, 0, "RESUME_FAILED")
    
    async def _execute_new_task(self, args):
        """Execute a new bulk mail task based on CLI arguments."""
        try:
            print(f"\nStarting new bulk email task")
            print(f"Email file: {args.email_file}")
            print(f"Template: {args.template}")
            print(f"Subject: {args.subject}")
            
            # session_manager.load_email_file 方法通过传入邮件文件路径
            # 加载邮箱地址列表，结果赋值给 emails 变量
            emails = self.session_manager.load_email_file(args.email_file)
            
            # len 函数计算邮件总数
            total_count = len(emails)
            print(f"Total emails: {total_count}")
            
            # _process_attachments 方法处理附件并优化参数
            # 为新任务单独处理附件和参数优化
            optimized_params = self._process_attachments(args)
            
            # BulkMailLogger 构造函数创建新的日志管理器实例
            self.logger = BulkMailLogger(args.log_file)
            
            # logger.start_session 方法通过传入任务参数
            # 开始新的邮件发送会话并记录日志
            self.logger.start_session(
                args.email_file,
                args.template, 
                total_count,
                args.subject
            )
            
            # _send_emails_with_progress 方法通过传入邮件列表和优化后的发送参数
            # 执行带进度显示的邮件发送过程，包含附件处理
            await self._send_emails_with_progress(
                emails,
                args.subject,
                args.template,
                optimized_params['batch_size'],
                optimized_params['delay'],
                args.attachments_dir
            )
            
        except Exception as e:
            print(f"New task execution failed: {e}")
            
            # if 条件检查日志管理器是否存在
            if self.logger:
                # logger.end_session 方法记录新任务执行失败
                self.logger.end_session(0, 0, 0, "TASK_FAILED")
    
    def _should_execute_new_task(self, incomplete_sessions: List[Dict[str, Any]], 
                                new_task: Dict[str, Any]) -> bool:
        """Return True if the new task is different from all incomplete sessions."""
        # for session in incomplete_sessions 遍历未完成会话
        for session in incomplete_sessions:
            # session_manager.compare_tasks 方法通过传入会话和新任务信息
            # 比较任务是否相同，结果赋值给 tasks_same 变量
            tasks_same = self.session_manager.compare_tasks(session, new_task)
            
            # if 条件检查任务是否相同
            if tasks_same:
                # 如果新任务与某个未完成会话相同，则不需要执行新任务
                return False
        
        # 新任务与所有未完成会话都不同时需要执行
        return True
    
    def _process_attachments(self, args) -> Dict[str, Any]:
        """Scan attachments directory and optimize sending parameters accordingly."""
        # optimized_params 被初始化为包含原始参数的字典
        optimized_params = {
            'batch_size': args.batch_size,
            'delay': args.delay,
            'has_attachments': False,
            'total_attachment_size_mb': 0
        }
        
        # if 条件检查是否指定了附件目录
        if args.attachments_dir:
            print(f"\nProcessing attachments...")
            
            try:
                # os.path.abspath 函数通过传入相对路径转换为绝对路径
                abs_attachments_dir = os.path.abspath(args.attachments_dir)
                
                # Path 构造函数创建附件目录路径对象
                attachments_path = Path(abs_attachments_dir)
                
                # attachments_path.exists 方法检查附件目录是否存在
                if not attachments_path.exists():
                    print(f"Attachments directory does not exist: {abs_attachments_dir}")
                    print("Ensure the directory exists or omit --attachments-dir")
                    return optimized_params
                
                # _scan_attachments_directory 方法通过传入附件目录路径
                # 扫描目录中的文件，返回附件统计信息
                attachment_info = self._scan_attachments_directory(abs_attachments_dir)
                
                # 检查是否有大小限制错误
                if attachment_info.get('error') == 'SIZE_LIMIT_EXCEEDED':
                    print(f"{attachment_info.get('error_message')}")
                    print("Continue without attachments")
                    return optimized_params
                
                # attachment_info.get 方法获取附件总大小
                total_size_mb = attachment_info.get('total_size_mb', 0)
                
                # attachment_info.get 方法获取附件文件数量
                file_count = attachment_info.get('total_files', 0)
                
                # if 条件检查是否找到了附件文件
                if file_count > 0:
                    # optimized_params 字典更新附件相关信息
                    optimized_params['has_attachments'] = True
                    optimized_params['total_attachment_size_mb'] = total_size_mb
                    
                    # _optimize_params_for_attachments 方法通过传入附件大小和原始参数
                    # 根据附件大小智能调整发送参数，返回优化建议
                    optimization = self._optimize_params_for_attachments(total_size_mb, args)
                    
                    # 应用优化建议
                    optimized_params['batch_size'] = optimization['batch_size']
                    optimized_params['delay'] = optimization['delay']
                    
                    # if 条件检查是否有参数调整
                    if optimization['adjusted']:
                        print(f"\nPARAM_OPTIMIZATION: Adjusted based on attachments size ({total_size_mb:.1f}MB)")
                        print(f"   batch size: {args.batch_size} -> {optimization['batch_size']}")
                        print(f"   delay: {args.delay} -> {optimization['delay']} seconds")
                        print(f"   estimated time: {optimization['estimated_time']}")
                        print("   using recommended parameters")
                else:
                    print("No valid files found in attachments directory")
                    
            except Exception as e:
                print(f"Error while processing attachments: {e}")
                print("Continue without attachments")
        
        # return 语句返回优化后的参数字典
        return optimized_params
    
    def _scan_attachments_directory(self, attachments_dir: str) -> Dict[str, Any]:
        """Scan attachment files in the directory and return statistics."""
        # Path 构造函数通过传入目录路径创建路径对象
        dir_path = Path(attachments_dir)
        
        # 初始化统计变量
        attachment_files = []
        total_size = 0
        skipped_files = []
        
        print(f"Scanning attachments directory: {attachments_dir}")
        
        # dir_path.iterdir 方法获取目录中所有文件的迭代器
        for file_path in dir_path.iterdir():
            # file_path.is_file 方法检查是否为普通文件
            if file_path.is_file():
                # file_path.name 属性获取文件名
                filename = file_path.name
                
                # _should_skip_attachment_file 方法检查是否应跳过此文件
                if self._should_skip_attachment_file(filename):
                    # skipped_files.append 方法添加跳过的文件名
                    skipped_files.append(filename)
                    continue
                
                # file_path.stat 方法获取文件统计信息
                file_stat = file_path.stat()
                
                # file_stat.st_size 属性获取文件大小字节数
                file_size = file_stat.st_size
                
                # file_size / (1024 * 1024) 计算MB大小
                file_size_mb = file_size / (1024 * 1024)
                
                # attachment_files.append 方法添加文件信息到列表
                attachment_files.append({
                    'name': filename,
                    'path': str(file_path),
                    'size_mb': file_size_mb
                })
                
                # total_size 累加文件大小
                total_size += file_size
                
                # print 函数输出找到的附件文件信息
                print(f"   Attachment: {filename} ({file_size_mb:.1f}MB)")
        
        # total_size_mb 计算总大小的MB值
        total_size_mb = total_size / (1024 * 1024)
        
        # 检查附件总大小是否超过12MB限制
        MAX_ATTACHMENT_SIZE_MB = 12.0
        if total_size_mb > MAX_ATTACHMENT_SIZE_MB:
            print(f"Total attachments size ({total_size_mb:.1f}MB) exceeds limit ({MAX_ATTACHMENT_SIZE_MB}MB)")
            print(f"Please reduce attachments or send in multiple batches")
            # 返回空的附件信息表示超过限制
            return {
                'total_files': 0,
                'total_size_mb': total_size_mb,
                'attachment_files': [],
                'skipped_files': skipped_files,
                'error': 'SIZE_LIMIT_EXCEEDED',
                'error_message': f'Total attachments size ({total_size_mb:.1f}MB) exceeds limit ({MAX_ATTACHMENT_SIZE_MB}MB)'
            }
        
        # print 函数输出附件扫描结果统计
        print(f"Found {len(attachment_files)} attachments, total size: {total_size_mb:.1f}MB")
        
        # if 条件检查是否有跳过的文件
        if skipped_files:
            # print 函数输出跳过的文件信息
            print(f"Skipped files: {', '.join(skipped_files)}")
        
        # return 语句返回附件扫描统计字典
        return {
            'total_files': len(attachment_files),
            'total_size_mb': total_size_mb,
            'attachment_files': attachment_files,
            'skipped_files': skipped_files
        }
    
    def _should_skip_attachment_file(self, filename: str) -> bool:
        """Return True if the file should be skipped as an attachment."""
        # filename.lower 方法将文件名转换为小写
        filename_lower = filename.lower()
        
        # 定义跳过文件的模式列表
        skip_patterns = [
            '.tmp', '.temp', '.cache', '.log', '.md',
            '.ds_store', 'thumbs.db', '.gitkeep', '.gitignore',
            '~', '.bak', '.backup', '.old'
        ]
        
        # for pattern in skip_patterns 遍历跳过模式
        for pattern in skip_patterns:
            # filename_lower.endswith 或 startswith 检查文件名模式
            if filename_lower.endswith(pattern) or filename_lower.startswith(pattern):
                return True
        
        # 没有匹配跳过模式时返回False
        return False
    
    def _optimize_params_for_attachments(self, total_size_mb: float, args) -> Dict[str, Any]:
        """Suggest batch size and delay based on total attachment size (MB)."""
        # 获取原始参数
        original_batch_size = args.batch_size
        original_delay = args.delay
        
        # 根据附件大小调整参数
        if total_size_mb <= 5:
            # 小附件：轻微调整
            recommended_batch_size = max(10, original_batch_size - 2)
            recommended_delay = max(1.0, original_delay)
            estimated_time = "5-10 minutes"
        elif total_size_mb <= 20:
            # 中附件：中度调整
            recommended_batch_size = max(5, original_batch_size // 2)
            recommended_delay = max(3.0, original_delay * 2)
            estimated_time = "15-30 minutes"
        else:
            # 大附件：大幅调整
            recommended_batch_size = min(3, max(1, original_batch_size // 5))
            recommended_delay = max(8.0, original_delay * 4)
            estimated_time = "45-90 minutes"
        
        # 判断是否有参数调整
        # 比较推荐参数与原始参数是否不同
        adjusted = (recommended_batch_size != original_batch_size or 
                   recommended_delay != original_delay)
        
        # return 语句返回优化建议字典
        return {
            'batch_size': recommended_batch_size,
            'delay': recommended_delay,
            'adjusted': adjusted,
            'estimated_time': estimated_time
        }
    
    async def _send_emails_with_progress(self, emails: List[str], subject: str, 
                                        template: str, batch_size: int, delay: float,
                                        attachments_dir: Optional[str] = None):
        """Send emails with progress (tqdm if available) and detailed logging."""
        try:
            # 导入进度条库
            from tqdm import tqdm
            TQDM_AVAILABLE = True
        except ImportError:
            TQDM_AVAILABLE = False
            print("tqdm not installed; using simple progress output")
        
        # len 函数获取邮件总数
        total_emails = len(emails)
        
        # 初始化统计变量
        # success_count 被初始化为0，统计成功发送数量
        success_count = 0
        
        # failed_count 被初始化为0，统计失败发送数量
        failed_count = 0
        
        # 创建进度条（如果可用）
        if TQDM_AVAILABLE:
            # tqdm 构造函数通过传入总数、描述和单位创建进度条
            # 结果赋值给 pbar 变量
            pbar = tqdm(total=total_emails, desc="Sending", unit="emails")
        
        # 计算批次信息
        # list 和 range 函数通过传入起始值、结束值和步长
        # 生成批次起始索引列表，结果赋值给 batches 变量
        batches = list(range(0, total_emails, batch_size))
        
        # len 函数计算总批次数
        total_batches = len(batches)
        
        print(f"Batches: {total_batches}, batch size: {batch_size}")
        
        # for batch_index, batch_start in enumerate(batches) 遍历每个批次
        for batch_index, batch_start in enumerate(batches):
            # self.interrupted 检查是否收到中断信号
            if self.interrupted:
                print("\nSending interrupted")
                break
            
            # min 函数通过传入批次结束位置和总数计算实际结束位置
            batch_end = min(batch_start + batch_size, total_emails)
            
            # 切片操作通过传入起始和结束位置获取当前批次邮箱列表
            current_batch = emails[batch_start:batch_end]
            
            print(f"\nProcessing batch {batch_index + 1}/{total_batches} ({len(current_batch)} emails)")
            
            # _send_single_batch 方法通过传入当前批次和邮件参数
            # 发送当前批次的邮件，包含附件处理，返回发送结果
            batch_success, batch_failed_details = await self._send_single_batch(
                current_batch, subject, template, attachments_dir
            )
            
            # 更新统计信息
            batch_success_count = len(batch_success)
            batch_failed_count = len(batch_failed_details)
            
            # success_count 累加当前批次的成功数量
            success_count += batch_success_count
            
            # failed_count 累加当前批次的失败数量
            failed_count += batch_failed_count
            
            # _log_batch_results 方法通过传入批次结果信息
            # 记录当前批次的详细发送结果到日志
            self._log_batch_results(batch_success, batch_failed_details)
            
            # logger.log_batch_complete 方法通过传入批次统计信息
            # 记录批次完成的日志条目
            self.logger.log_batch_complete(
                batch_index + 1, total_batches, 
                batch_success_count, len(current_batch)
            )
            
            # 更新进度条
            if TQDM_AVAILABLE:
                # pbar.update 方法通过传入当前批次的邮件数量更新进度
                pbar.update(len(current_batch))
                
                # pbar.set_postfix 方法通过传入统计信息字典
                # 更新进度条后缀显示的统计信息
                pbar.set_postfix({
                    'success': success_count,
                    'failed': failed_count,
                    'rate': f"{(success_count / (success_count + failed_count) * 100):.1f}%" if (success_count + failed_count) > 0 else "0%"
                })
            
            # 批次间延迟控制
            # if 条件检查是否不是最后一个批次且需要延迟
            if batch_index < total_batches - 1 and delay > 0:
                print(f"Waiting {delay} seconds before next batch...")
                
                # asyncio.sleep 函数通过传入延迟秒数异步暂停
                await asyncio.sleep(delay)
        
        # 关闭进度条
        if TQDM_AVAILABLE:
            # pbar.close 方法关闭进度条显示
            pbar.close()
        
        # 记录会话结束
        if self.logger:
            # 确定会话结束状态
            session_status = "INTERRUPTED" if self.interrupted else "COMPLETED"
            
            # logger.end_session 方法通过传入最终统计信息和状态
            # 记录会话结束日志
            self.logger.end_session(total_emails, success_count, failed_count, session_status)
        
        # 输出最终统计
        # success_rate 计算成功率百分比
        success_rate = (success_count / total_emails * 100) if total_emails > 0 else 0
        
        print(f"\nSend summary:")
        print(f"Succeeded: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Success rate: {success_rate:.1f}%")
    
    async def _send_single_batch(self, emails: List[str], subject: str, 
                                template: str, attachments_dir: Optional[str] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Send a single batch of emails and return (success_emails, failed_details)."""
        # session_manager.validate_template_exists 方法检查模板是否存在
        template_exists = self.session_manager.validate_template_exists(template)
        
        # if 条件检查模板是否存在
        if template_exists:
            # _send_batch_with_attachments 方法通过传入邮箱列表、邮件参数和附件目录
            # 发送包含附件的邮件批次，返回详细结果
            return await self._send_batch_with_attachments(
                emails, subject, template, attachments_dir
            )
        else:
            # 模板不存在时构造所有邮件的失败信息
            print(f"Template not found: '{template}'")
            
            # 为所有邮件构造模板不存在的错误信息
            failed_details = []
            for email in emails:
                failed_detail = {
                    'email': email,
                    'error_type': 'TemplateError',
                    'error_message': f'Template {template} not found',
                    'timestamp': datetime.now().isoformat(),
                    'success': False
                }
                # failed_details.append 方法添加错误详情
                failed_details.append(failed_detail)
            
            # return 语句返回空的成功列表和所有邮件的失败详情
            return [], failed_details
    
    async def _send_batch_with_attachments(self, emails: List[str], subject: str, 
                                          template: str, attachments_dir: Optional[str] = None) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Send a batch with attachments; return (success_emails, failed_details)."""
        # 导入邮件消息类用于创建包含附件的邮件
        from shared_utilities.mail.SendMail import EmailMessage, mail_sender
        
        # 初始化结果列表
        success_emails = []
        failed_details = []
        
        # for email in emails 遍历当前批次的每个邮箱地址
        for email in emails:
            try:
                # EmailMessage 构造函数通过传入收件人、主题、模板信息
                # 创建邮件消息对象，结果赋值给 email_msg 变量
                email_msg = EmailMessage(
                    to=email,
                    subject=subject,
                    template_name=template,
                    template_vars={},  # 使用空的模板变量
                    content_type='html'
                )
                
                # if 条件检查是否指定了附件目录
                if attachments_dir:
                    # email_msg.add_attachments_from_directory 方法通过传入附件目录
                    # 扫描并添加目录中的所有附件到邮件中
                    email_msg.add_attachments_from_directory(attachments_dir)
                
                # mail_sender.send_email 方法通过传入邮件消息对象
                # 异步发送邮件，返回详细结果字典
                send_result = await mail_sender.send_email(email_msg)
                
                # send_result.get 方法通过传入 'success' 键检查发送是否成功
                if send_result.get('success', False):
                    # success_emails.append 方法将成功邮箱添加到成功列表
                    success_emails.append(email)
                else:
                    # failed_details.append 方法将发送失败的详细信息添加到失败列表
                    failed_details.append(send_result)
                    
            except Exception as e:
                # 异常情况下构造详细错误信息字典
                error_detail = {
                    'email': email,
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'timestamp': datetime.now().isoformat(),
                    'success': False
                }
                
                # failed_details.append 方法将异常错误信息添加到失败列表
                failed_details.append(error_detail)
        
        # return 语句返回成功邮箱列表和失败详情列表的元组
        return success_emails, failed_details
    
    def _log_batch_results(self, success_emails: List[str], failed_details: List[Dict[str, Any]]):
        """Write batch results to the detailed log."""
        # for email in success_emails 遍历成功发送的邮箱
        for email in success_emails:
            # logger.log_email_result 方法通过传入邮箱和成功状态
            # 记录邮件发送成功的日志条目
            self.logger.log_email_result(email, True)
        
        # for failed_detail in failed_details 遍历失败发送的详情
        for failed_detail in failed_details:
            # failed_detail.get 方法获取失败邮箱地址
            email = failed_detail.get('email', 'unknown')
            
            # logger.log_email_result 方法通过传入邮箱、失败状态和错误详情
            # 记录邮件发送失败的详细日志条目
            self.logger.log_email_result(email, False, failed_detail)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the CLI argument parser."""
    # argparse.ArgumentParser 构造函数通过传入描述信息
    # 创建命令行参数解析器，结果赋值给 parser 变量
    parser = argparse.ArgumentParser(
        description='Career Bot bulk mail sender',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python BulkMail.py emails.txt verification --subject \"Your Verification Code\"\n"
            "  python BulkMail.py users.txt welcome --subject \"Welcome\" --batch-size 20\n"
            "  python BulkMail.py vips.txt marketing --subject \"VIP Offer\" --delay 5.0\n"
        )
    )
    
    # parser.add_argument 方法通过传入位置参数名和帮助信息
    # 添加邮箱文件路径的必需参数
    parser.add_argument('email_file', 
                       help='Path to the text file containing email addresses')
    
    # parser.add_argument 方法添加模板名称的必需参数
    parser.add_argument('template',
                       help='Mail template name (e.g., verification, welcome, marketing)')
    
    # parser.add_argument 方法通过传入参数名、类型和帮助信息
    # 添加邮件主题的必需参数
    parser.add_argument('--subject', '-s',
                       required=True,
                       help='Email subject')
    
    # parser.add_argument 方法添加批次大小的可选参数
    parser.add_argument('--batch-size', '-b',
                       type=int,
                       default=15,
                       help='Number of emails per batch (default: 15)')
    
    # parser.add_argument 方法添加延迟时间的可选参数
    parser.add_argument('--delay', '-d',
                       type=float,
                       default=2.0,
                       help='Delay in seconds between batches (default: 2.0)')
    
    # parser.add_argument 方法添加日志文件路径的可选参数
    parser.add_argument('--log-file', '-l',
                       help='Custom log file path (optional)')
    
    # parser.add_argument 方法添加强制恢复的标志参数
    parser.add_argument('--resume', '-r',
                       action='store_true',
                       help='Force resume incomplete tasks (skip interactive prompt)')
    
    # parser.add_argument 方法添加附件目录的可选参数
    parser.add_argument('--attachments-dir', '-a',
                       help='Attachments directory (all files will be attached)')
    
    # parser.add_argument 方法添加清理旧日志的可选参数
    parser.add_argument('--clean-logs',
                       type=int,
                       metavar='DAYS',
                       help='Delete log files older than N days')
    
    # return 语句返回配置好的参数解析器
    return parser


async def main():
    """Program entry: parse args, initialize sender, run tasks."""
    # create_argument_parser 函数创建参数解析器
    parser = create_argument_parser()
    
    # parser.parse_args 方法解析命令行参数，结果赋值给 args 变量
    args = parser.parse_args()
    
    # 处理日志清理功能
    if args.clean_logs:
        print(f"Cleaning old log files older than {args.clean_logs} days...")
        
        # SessionManager 构造函数创建会话管理器实例
        session_manager = SessionManager()
        
        # session_manager.clean_old_logs 方法通过传入保留天数
        # 清理过期的日志文件
        session_manager.clean_old_logs(args.clean_logs)
        
        print("Log cleanup completed")
        return 0
    
    # 验证邮箱文件是否存在
    # Path 构造函数通过传入邮箱文件路径创建路径对象
    email_file_path = Path(args.email_file)
    
    # email_file_path.exists 方法检查邮箱文件是否存在
    if not email_file_path.exists():
        print(f"Email file not found: {args.email_file}")
        return 1
    
    # 创建批量邮件发送器实例
    # BulkMailSender 构造函数创建发送器实例，结果赋值给 sender 变量
    sender = BulkMailSender()
    
    try:
        # sender.process_args 方法通过传入命令行参数
        # 异步处理邮件发送任务，返回程序退出码
        exit_code = await sender.process_args(args)
        
        # return 语句返回任务处理的退出码
        return exit_code
        
    except KeyboardInterrupt:
        print("\nUser interrupted execution")
        return 0
    except Exception as e:
        print(f"Program execution failed: {e}")
        return 1
    finally:
        # 确保日志管理器正确关闭
        if sender.logger:
            # sender.logger.close 方法关闭日志文件句柄
            sender.logger.close()


if __name__ == "__main__":
    """Script entry point: run the async main and exit with code."""
    try:
        # asyncio.run 函数通过传入主程序协程运行异步任务
        # 获取程序退出码，结果赋值给 exit_code 变量
        exit_code = asyncio.run(main())
        
        # sys.exit 函数通过传入退出码结束程序运行
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\nGoodbye!")
        # sys.exit 函数通过传入0正常退出程序
        sys.exit(0)
