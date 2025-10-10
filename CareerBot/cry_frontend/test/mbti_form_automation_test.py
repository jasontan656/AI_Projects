#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MBTI表单自动化测试脚本 - 浏览器点击模拟测试
职责：分析为什么点击生成的首批1/8表单不会触发前后端联动自动存储机制

设计哲学：
- 详细日志记录每个步骤
- 精确模拟用户行为
- 分析网络请求和响应
- 监控DOM变化和事件触发
- 验证formStateManager的10秒防抖机制

测试目标：
1. 验证Take Test按钮点击后是否生成表单
2. 检查表单是否具有正确的唯一ID
3. 模拟选择表单选项
4. 监控是否触发10秒倒计时
5. 验证state_sync请求是否发送到后端
6. 分析失败原因并提供解决方案

作者: AI Assistant
创建日期: 2024-09-17
版本: 1.0.0
"""

import os
import sys
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# 导入Selenium相关模块
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# 导入WebDriver管理器
from webdriver_manager.chrome import ChromeDriverManager

# 导入请求处理模块
import requests


class MBTIFormTester:
    """
    MBTI表单自动化测试器
    
    设计理念：
    - 模拟真实用户操作流程
    - 详细记录每个步骤和网络请求
    - 分析前后端交互失败原因
    - 提供可重现的测试环境
    """
    
    def __init__(self, frontend_url: str = "http://localhost:5173", backend_url: str = "http://localhost:8000"):
        """
        初始化测试器
        
        Args:
            frontend_url: 前端服务URL
            backend_url: 后端服务URL
        """
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.driver: Optional[webdriver.Chrome] = None
        
        # 创建日志目录
        self.test_dir = Path(__file__).parent
        self.log_dir = self.test_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # 设置详细日志
        self.setup_logging()
        
        # 测试状态追踪
        self.test_session = {
            "start_time": datetime.now(),
            "form_id": None,
            "form_clicks": [],
            "network_requests": [],
            "errors": [],
            "success_steps": []
        }
        
        self.logger.info("🚀 MBTI表单自动化测试器初始化完成")
        self.logger.info(f"前端URL: {self.frontend_url}")
        self.logger.info(f"后端URL: {self.backend_url}")
    
    def setup_logging(self):
        """设置详细的日志记录系统"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"mbti_test_{timestamp}.log"
        
        # 创建logger
        self.logger = logging.getLogger('MBTIFormTester')
        self.logger.setLevel(logging.DEBUG)
        
        # 清除已存在的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # 文件处理器 - 详细日志
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(funcName)-20s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # 控制台处理器 - 关键信息
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"📝 日志文件: {log_file}")
    
    def setup_chrome_driver(self) -> bool:
        """
        配置和启动Chrome浏览器
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            self.logger.info("🌐 正在配置Chrome浏览器...")
            
            # Chrome选项配置
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--window-size=1920,1080")
            
            # 启用网络日志记录
            chrome_options.add_argument("--enable-logging")
            chrome_options.add_argument("--log-level=0")
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
            
            # 获取ChromeDriver
            service = Service(ChromeDriverManager().install())
            
            # 创建浏览器实例
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info(f"✅ Chrome浏览器启动成功: {self.driver.capabilities['browserVersion']}")
            self.test_session["success_steps"].append("Chrome浏览器配置成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Chrome浏览器配置失败: {str(e)}")
            self.test_session["errors"].append(f"浏览器配置失败: {str(e)}")
            return False
    
    def check_services_status(self) -> Dict[str, bool]:
        """
        检查前后端服务状态
        
        Returns:
            Dict[str, bool]: 服务状态字典
        """
        status = {"frontend": False, "backend": False}
        
        # 检查前端服务
        try:
            self.logger.info(f"🔍 检查前端服务: {self.frontend_url}")
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code == 200:
                status["frontend"] = True
                self.logger.info("✅ 前端服务正常")
            else:
                self.logger.warning(f"⚠️ 前端服务响应异常: {response.status_code}")
        except Exception as e:
            self.logger.error(f"❌ 前端服务不可达: {str(e)}")
            self.test_session["errors"].append(f"前端服务不可达: {str(e)}")
        
        # 检查后端服务
        try:
            self.logger.info(f"🔍 检查后端服务: {self.backend_url}")
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            if response.status_code == 200:
                status["backend"] = True
                self.logger.info("✅ 后端服务正常")
            else:
                self.logger.warning(f"⚠️ 后端服务响应异常: {response.status_code}")
        except Exception as e:
            self.logger.error(f"❌ 后端服务不可达: {str(e)}")
            self.test_session["errors"].append(f"后端服务不可达: {str(e)}")
        
        return status
    
    def navigate_to_frontend(self) -> bool:
        """
        导航到前端页面
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            self.logger.info(f"🧭 导航到前端页面: {self.frontend_url}")
            self.driver.get(self.frontend_url)
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 记录页面信息
            title = self.driver.title
            current_url = self.driver.current_url
            
            self.logger.info(f"📄 页面标题: {title}")
            self.logger.info(f"🔗 当前URL: {current_url}")
            
            self.test_session["success_steps"].append("成功导航到前端页面")
            return True
            
        except TimeoutException:
            self.logger.error("❌ 页面加载超时")
            self.test_session["errors"].append("页面加载超时")
            return False
        except Exception as e:
            self.logger.error(f"❌ 导航失败: {str(e)}")
            self.test_session["errors"].append(f"导航失败: {str(e)}")
            return False
    
    def click_personality_assessment(self) -> bool:
        """
        先点击"personality assessment"按钮触发Take Test按钮显示
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        self.logger.info("🔍 寻找并点击 Personality Assessment 按钮...")
        
        # 可能的personality assessment按钮选择器
        assessment_selectors = [
            "//a[contains(text(), 'Start personality assessment')]",
            "//a[@class='group-link group-link--DevComplete']",
            "//a[contains(@class, 'group-link--DevComplete')]",
            "//a[contains(text(), 'personality assessment')]",
            "//button[contains(text(), 'personality assessment')]",
            "//button[contains(text(), 'Personality Assessment')]",
            "//a[contains(text(), 'Personality Assessment')]",
            "//button[contains(text(), '性格测评')]",
            "//*[contains(text(), 'MBTI')]",
            "//button[contains(@class, 'assessment')]",
            "//*[@data-intent='mbti']"
        ]
        
        for i, selector in enumerate(assessment_selectors):
            try:
                self.logger.debug(f"尝试personality assessment选择器 {i+1}/{len(assessment_selectors)}: {selector}")
                element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                self.logger.info(f"✅ 找到Personality Assessment按钮，使用选择器: {selector}")
                
                # 滚动到元素并点击
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                element.click()
                
                self.logger.info("✅ Personality Assessment按钮点击成功")
                self.test_session["success_steps"].append("Personality Assessment按钮点击成功")
                
                # 等待Take Test按钮出现
                time.sleep(2)
                return True
                
            except TimeoutException:
                self.logger.debug(f"选择器 {i+1} 超时，尝试下一个...")
                continue
            except Exception as e:
                self.logger.debug(f"选择器 {i+1} 出错: {str(e)}")
                continue
        
        # 如果所有选择器都失败，尝试查找页面上包含相关关键词的所有元素
        self.logger.warning("🔍 所有预定义选择器失败，搜索页面中包含相关关键词的元素...")
        try:
            all_clickable = self.driver.find_elements(By.XPATH, "//*[self::button or self::a]")
            for element in all_clickable:
                text = element.text.strip().lower()
                if any(keyword in text for keyword in ['personality', 'assessment', 'mbti', '性格', '测评']):
                    self.logger.info(f"✅ 通过关键词搜索找到元素: '{element.text.strip()}'")
                    element.click()
                    self.logger.info("✅ Personality Assessment相关按钮点击成功")
                    self.test_session["success_steps"].append(f"点击了包含关键词的按钮: {element.text.strip()}")
                    time.sleep(2)
                    return True
        except Exception as e:
            self.logger.debug(f"关键词搜索时出错: {str(e)}")
        
        self.logger.error("❌ 未找到Personality Assessment按钮")
        self.test_session["errors"].append("未找到Personality Assessment按钮")
        return False

    def handle_login_requirement(self) -> bool:
        """
        处理登录要求，如果页面显示需要登录则自动登录
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        self.logger.info("🔍 检查是否需要登录...")
        
        try:
            # 检查页面是否显示登录要求
            login_required_texts = [
                "requires you to be logged in",
                "Please sign in",
                "需要登录",
                "Login / Sign Up"
            ]
            
            page_source = self.driver.page_source.lower()
            needs_login = any(text.lower() in page_source for text in login_required_texts)
            
            if needs_login:
                self.logger.info("🔐 检测到需要登录，开始自动登录流程...")
                return self.perform_login()
            else:
                self.logger.info("✅ 无需登录，可直接进行测试")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 检查登录要求失败: {str(e)}")
            self.test_session["errors"].append(f"检查登录要求失败: {str(e)}")
            return False

    def perform_login(self) -> bool:
        """
        执行自动登录
        
        Returns:
            bool: 登录成功返回True，失败返回False
        """
        try:
            self.logger.info("🔑 开始自动登录流程...")
            
            # 1. 点击Login / Sign Up按钮
            login_selectors = [
                "//a[contains(text(), 'Login / Sign Up')]",
                "//button[contains(text(), 'Login')]",
                "//a[contains(text(), '登录')]",
                "//*[@class='message-link message-link--DevComplete']",
                "//a[contains(@class, 'message-link')]"
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    login_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.logger.info(f"✅ 找到登录按钮，使用选择器: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not login_button:
                self.logger.error("❌ 未找到登录按钮")
                self.test_session["errors"].append("未找到登录按钮")
                return False
            
            # 点击登录按钮
            self.driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
            time.sleep(0.5)
            login_button.click()
            self.logger.info("✅ 登录按钮点击成功")
            
            # 等待登录模态窗口出现
            time.sleep(2)
            
            # 2. 填写登录表单
            self.logger.info("📝 填写登录表单...")
            
            # 查找邮箱输入框
            email_selectors = [
                "//input[@type='email']",
                "//input[@placeholder*='email']",
                "//input[@placeholder*='邮箱']",
                "//input[@name='email']",
                "//input[@id='email']"
            ]
            
            email_input = None
            for selector in email_selectors:
                try:
                    email_input = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    self.logger.info(f"✅ 找到邮箱输入框，使用选择器: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not email_input:
                self.logger.error("❌ 未找到邮箱输入框")
                self.test_session["errors"].append("未找到邮箱输入框")
                return False
            
            # 输入邮箱
            email_input.clear()
            email_input.send_keys("jason.tan656@gmail.com")
            self.logger.info("✅ 邮箱输入完成: jason.tan656@gmail.com")
            
            # 查找密码输入框
            password_selectors = [
                "//input[@type='password']",
                "//input[@placeholder*='password']",
                "//input[@placeholder*='密码']",
                "//input[@name='password']",
                "//input[@id='password']"
            ]
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    self.logger.info(f"✅ 找到密码输入框，使用选择器: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not password_input:
                self.logger.error("❌ 未找到密码输入框")
                self.test_session["errors"].append("未找到密码输入框")
                return False
            
            # 输入密码
            password_input.clear()
            password_input.send_keys("w8913720")
            self.logger.info("✅ 密码输入完成")
            
            # 3. 提交登录表单
            submit_selectors = [
                "//button[@type='submit']",
                "//button[contains(text(), 'Login')]",
                "//button[contains(text(), '登录')]",
                "//button[contains(@class, 'login-btn')]",
                "//button[contains(@class, 'submit-btn')]"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.logger.info(f"✅ 找到提交按钮，使用选择器: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not submit_button:
                self.logger.error("❌ 未找到提交按钮")
                self.test_session["errors"].append("未找到提交按钮")
                return False
            
            # 点击提交按钮
            submit_button.click()
            self.logger.info("✅ 登录表单提交成功")
            
            # 4. 等待登录完成并详细检查状态
            self.logger.info("⏳ 等待登录处理完成...")
            
            # 循环检查登录状态变化
            for attempt in range(15):  # 最多等待30秒
                time.sleep(2)
                current_source = self.driver.page_source.lower()
                
                self.logger.debug(f"登录检查尝试 {attempt + 1}/15...")
                
                # 检查是否有错误消息
                if "invalid" in current_source or "错误" in current_source or "failed" in current_source:
                    self.logger.error("❌ 检测到登录错误消息")
                    self.test_session["errors"].append("登录凭据可能错误")
                    return False
                
                # 检查是否还有登录要求
                if "requires you to be logged in" not in current_source:
                    self.logger.info("✅ 登录要求消息已消失，检查新消息...")
                    
                    # 检查是否有新的AI消息出现
                    messages = self.driver.find_elements(By.CSS_SELECTOR, ".message-bubble")
                    self.logger.info(f"📊 当前消息泡泡数量: {len(messages)}")
                    
                    # 检查是否有Take Test相关按钮
                    take_test_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Take Test') or contains(text(), 'take test')]")
                    if take_test_elements:
                        self.logger.info(f"🎯 找到 {len(take_test_elements)} 个Take Test相关元素")
                        for i, elem in enumerate(take_test_elements):
                            self.logger.info(f"  Element {i+1}: {elem.tag_name} - '{elem.text.strip()}' - Class: '{elem.get_attribute('class')}'")
                    
                    self.logger.info("✅ 登录成功，继续测试流程")
                    self.test_session["success_steps"].append("用户登录成功")
                    return True
                
                # 检查消息数量是否增加（表示有新响应）
                current_messages = len(self.driver.find_elements(By.CSS_SELECTOR, ".message-bubble"))
                if current_messages > 2:  # 初始有2个消息
                    self.logger.info(f"📨 检测到新消息，当前消息数量: {current_messages}")
            
            # 超时后做最终检查
            final_source = self.driver.page_source.lower()
            if "requires you to be logged in" in final_source:
                self.logger.error("❌ 登录超时失败，仍显示登录要求")
                self.test_session["errors"].append("登录超时失败")
                return False
            else:
                self.logger.warning("⚠️ 登录状态不明确，但继续测试")
                return True
                    
        except Exception as e:
            self.logger.error(f"❌ 登录处理失败: {str(e)}")
            self.test_session["errors"].append(f"登录处理失败: {str(e)}")
            return False

    def wait_for_take_test_button(self, timeout: int = 30) -> Optional[Any]:
        """
        等待"Take Test"按钮出现并返回元素
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            WebElement: Take Test按钮元素，或None
        """
        self.logger.info("🔍 等待Take Test按钮出现...")
        
        # 可能的按钮选择器（登录后的结构）
        selectors = [
            "//a[contains(text(), 'Take Test')]",
            "//button[contains(text(), 'Take Test')]",
            "//*[contains(text(), 'Take Test')]",
            "//button[@id='mbti_assessment']",
            "//a[contains(@class, 'DevComplete')]",
            "//button[contains(@class, 'DevComplete')]",
            "//*[@data-intent='mbti_start']",
            "//a[@class='message-link message-link--DevComplete']",
            "//*[@class='group-link group-link--DevComplete']"
        ]
        
        for i, selector in enumerate(selectors):
            try:
                self.logger.debug(f"尝试选择器 {i+1}/{len(selectors)}: {selector}")
                element = WebDriverWait(self.driver, timeout // len(selectors)).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                self.logger.info(f"✅ 找到Take Test按钮，使用选择器: {selector}")
                return element
            except TimeoutException:
                self.logger.debug(f"选择器 {i+1} 超时，尝试下一个...")
                continue
            except Exception as e:
                self.logger.debug(f"选择器 {i+1} 出错: {str(e)}")
                continue
        
        # 如果所有选择器都失败，尝试查找页面上的所有可点击元素
        self.logger.warning("🔍 所有预定义选择器失败，搜索页面中的所有可点击元素...")
        try:
            # 检查当前页面状态
            current_messages = len(self.driver.find_elements(By.CSS_SELECTOR, ".message-bubble"))
            self.logger.info(f"📊 当前页面消息数量: {current_messages}")
            
            # 搜索所有可能包含Take Test的元素
            all_clickable = self.driver.find_elements(By.XPATH, "//*[self::button or self::a or @onclick or contains(@class, 'clickable') or contains(@class, 'btn')]")
            self.logger.info(f"📊 找到 {len(all_clickable)} 个可点击元素")
            
            for element in all_clickable:
                text = element.text.strip()
                if text and ("take" in text.lower() and "test" in text.lower()):
                    self.logger.info(f"✅ 通过文本搜索找到Take Test元素: '{text}' - {element.tag_name}")
                    return element
            
            # 如果没找到，打印当前页面的所有链接和按钮供调试
            self.logger.warning("🔍 未找到Take Test，打印当前页面的所有链接和按钮...")
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            
            self.logger.info(f"📋 页面链接 ({len(all_links)}个):")
            for i, link in enumerate(all_links[:10]):  # 只显示前10个
                text = link.text.strip()
                if text:
                    self.logger.info(f"  链接 {i+1}: '{text}' - Class: '{link.get_attribute('class')}'")
            
            self.logger.info(f"📋 页面按钮 ({len(all_buttons)}个):")
            for i, btn in enumerate(all_buttons[:10]):  # 只显示前10个
                text = btn.text.strip()
                if text:
                    self.logger.info(f"  按钮 {i+1}: '{text}' - Class: '{btn.get_attribute('class')}'")
            
        except Exception as e:
            self.logger.debug(f"搜索页面元素时出错: {str(e)}")
        
        # 在真正失败前，暂停让用户查看
        self.logger.error("❌ 未找到Take Test按钮")
        self.logger.info("🔍 暂停5秒让浏览器保持打开状态供检查...")
        time.sleep(5)
        
        self.test_session["errors"].append("未找到Take Test按钮")
        return None
    
    def take_screenshot(self, step_name: str) -> str:
        """
        截取当前页面截图
        
        Args:
            step_name: 步骤名称
            
        Returns:
            str: 截图文件路径
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.log_dir / f"screenshot_{step_name}_{timestamp}.png"
            self.driver.save_screenshot(str(screenshot_path))
            self.logger.info(f"📸 截图已保存: {screenshot_path}")
            return str(screenshot_path)
        except Exception as e:
            self.logger.error(f"❌ 截图失败: {str(e)}")
            return ""

    def click_take_test_button(self) -> bool:
        """
        点击Take Test按钮
        
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            # 等待一段时间确保页面完全加载
            self.logger.info("⏳ 等待页面稳定后查找Take Test按钮...")
            time.sleep(3)
            
            # 截图记录当前状态
            self.take_screenshot("before_take_test_search")
            
            # 找到Take Test按钮
            take_test_button = self.wait_for_take_test_button()
            if not take_test_button:
                # 截图记录失败状态
                self.take_screenshot("take_test_button_not_found")
                return False
            
            # 记录点击前的状态
            self.logger.info("📸 记录点击前状态...")
            before_click_url = self.driver.current_url
            button_text = take_test_button.text.strip()
            button_class = take_test_button.get_attribute('class')
            
            self.logger.info(f"🎯 准备点击按钮: '{button_text}' - Class: '{button_class}'")
            
            # 截图记录点击前状态
            self.take_screenshot("before_take_test_click")
            
            # 点击按钮
            self.logger.info("🖱️ 点击Take Test按钮...")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", take_test_button)
            time.sleep(0.5)
            take_test_button.click()
            
            # 记录点击事件
            click_time = datetime.now()
            self.test_session["form_clicks"].append({
                "element": "take_test_button",
                "text": button_text,
                "class": button_class,
                "time": click_time,
                "before_url": before_click_url
            })
            
            self.logger.info(f"✅ Take Test按钮点击成功 - {click_time}")
            self.test_session["success_steps"].append("Take Test按钮点击成功")
            
            # 等待页面响应并截图
            self.logger.info("⏳ 等待Take Test点击后的页面响应...")
            time.sleep(3)
            self.take_screenshot("after_take_test_click")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 点击Take Test按钮失败: {str(e)}")
            self.test_session["errors"].append(f"点击Take Test按钮失败: {str(e)}")
            # 截图记录错误状态
            self.take_screenshot("take_test_click_error")
            return False
    
    def wait_for_form_generation(self, timeout: int = 30) -> Optional[str]:
        """
        等待MBTI表单生成并获取表单ID
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            str: 表单ID，或None
        """
        self.logger.info("⏳ 等待MBTI表单生成...")
        
        # 可能的表单选择器
        form_selectors = [
            "//div[starts-with(@id, 'form-')]",
            "//div[@data-form-type='mbti']",
            "//div[contains(@class, 'message-form')]",
            "//form[contains(@class, 'mbti')]",
            "//*[@data-form-id]"
        ]
        
        for selector in form_selectors:
            try:
                self.logger.debug(f"尝试表单选择器: {selector}")
                form_element = WebDriverWait(self.driver, timeout // len(form_selectors)).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                
                # 尝试获取表单ID
                form_id = None
                for attr in ['id', 'data-form-id', 'data-form-type']:
                    value = form_element.get_attribute(attr)
                    if value and ('form-' in value or 'mbti' in value):
                        form_id = value
                        break
                
                if form_id:
                    self.logger.info(f"✅ 找到MBTI表单，ID: {form_id}")
                    self.test_session["form_id"] = form_id
                    self.test_session["success_steps"].append(f"表单生成成功，ID: {form_id}")
                    return form_id
                else:
                    self.logger.warning(f"找到表单元素但无法确定ID: {form_element.tag_name}")
                    
            except TimeoutException:
                self.logger.debug(f"表单选择器超时: {selector}")
                continue
            except Exception as e:
                self.logger.debug(f"表单选择器出错: {selector} - {str(e)}")
                continue
        
        self.logger.error("❌ 未找到生成的MBTI表单")
        self.test_session["errors"].append("未找到生成的MBTI表单")
        return None
    
    def analyze_form_structure(self, form_id: str) -> Dict[str, Any]:
        """
        分析表单结构和ID系统
        
        Args:
            form_id: 表单ID
            
        Returns:
            Dict[str, Any]: 表单结构分析结果
        """
        self.logger.info(f"🔍 分析表单结构: {form_id}")
        
        analysis = {
            "form_id": form_id,
            "questions": [],
            "options": [],
            "has_unique_ids": False,
            "form_type": None,
            "structure_valid": False
        }
        
        try:
            # 查找表单容器
            form_element = self.driver.find_element(By.ID, form_id)
            analysis["form_type"] = form_element.get_attribute("data-form-type")
            
            # 查找所有题目
            question_selectors = [
                f"#{form_id} .form-question",
                f"#{form_id} [data-question-index]",
                f"#{form_id} .question"
            ]
            
            questions_found = []
            for selector in question_selectors:
                try:
                    questions = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if questions:
                        questions_found = questions
                        self.logger.info(f"✅ 找到 {len(questions)} 个题目，使用选择器: {selector}")
                        break
                except Exception as e:
                    self.logger.debug(f"题目选择器失败: {selector} - {str(e)}")
            
            # 分析每个题目
            for i, question in enumerate(questions_found):
                question_info = {
                    "index": i,
                    "id": question.get_attribute("id"),
                    "data_attributes": {},
                    "options": []
                }
                
                # 收集data属性
                for attr in question.get_property("attributes"):
                    attr_name = attr.get("name", "")
                    if attr_name.startswith("data-"):
                        question_info["data_attributes"][attr_name] = question.get_attribute(attr_name)
                
                # 查找选项
                options = question.find_elements(By.CSS_SELECTOR, ".radio-option, .radio-input, input[type='radio']")
                for j, option in enumerate(options):
                    option_info = {
                        "index": j,
                        "id": option.get_attribute("id"),
                        "name": option.get_attribute("name"),
                        "value": option.get_attribute("value"),
                        "data_attributes": {}
                    }
                    
                    # 收集选项的data属性
                    for attr in option.get_property("attributes"):
                        attr_name = attr.get("name", "")
                        if attr_name.startswith("data-"):
                            option_info["data_attributes"][attr_name] = option.get_attribute(attr_name)
                    
                    question_info["options"].append(option_info)
                
                analysis["questions"].append(question_info)
            
            # 检查ID系统是否完整
            has_form_id = bool(form_id)
            has_question_ids = all(q.get("id") for q in analysis["questions"])
            has_option_ids = all(
                opt.get("id") for q in analysis["questions"] for opt in q["options"]
            )
            
            analysis["has_unique_ids"] = has_form_id and has_question_ids and has_option_ids
            analysis["structure_valid"] = len(analysis["questions"]) > 0
            
            self.logger.info(f"📊 表单结构分析完成:")
            self.logger.info(f"  - 表单ID: {form_id}")
            self.logger.info(f"  - 题目数量: {len(analysis['questions'])}")
            self.logger.info(f"  - 总选项数量: {sum(len(q['options']) for q in analysis['questions'])}")
            self.logger.info(f"  - 唯一ID系统: {'✅ 完整' if analysis['has_unique_ids'] else '❌ 不完整'}")
            
            self.test_session["success_steps"].append("表单结构分析完成")
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ 表单结构分析失败: {str(e)}")
            self.test_session["errors"].append(f"表单结构分析失败: {str(e)}")
            return analysis
    
    def simulate_form_interaction(self, form_id: str, analysis: Dict[str, Any]) -> bool:
        """
        模拟表单交互（选择选项）
        
        Args:
            form_id: 表单ID
            analysis: 表单结构分析结果
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        if not analysis["questions"]:
            self.logger.error("❌ 没有找到可交互的题目")
            return False
        
        self.logger.info("🖱️ 开始模拟表单交互...")
        
        interactions = []
        
        try:
            # 对每个题目选择一个选项
            for i, question in enumerate(analysis["questions"][:3]):  # 只测试前3题
                if not question["options"]:
                    self.logger.warning(f"题目 {i} 没有可选选项")
                    continue
                
                # 选择第一个可用选项
                option = question["options"][0]
                option_id = option.get("id")
                
                if not option_id:
                    self.logger.warning(f"题目 {i} 选项没有ID")
                    continue
                
                try:
                    # 通过ID查找选项元素
                    option_element = self.driver.find_element(By.ID, option_id)
                    
                    # 记录交互前状态
                    before_interaction = {
                        "time": datetime.now(),
                        "question_index": i,
                        "option_id": option_id,
                        "option_value": option.get("value"),
                        "field_id": option.get("data_attributes", {}).get("data-field-id")
                    }
                    
                    # 滚动到元素并点击
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", option_element)
                    time.sleep(0.5)
                    
                    self.logger.info(f"🎯 点击选项: 题目{i} - 选项{option.get('value')} - ID:{option_id}")
                    
                    # 截图记录点击前状态
                    self.take_screenshot(f"before_option_click_q{i}")
                    
                    option_element.click()
                    
                    # 记录交互后状态
                    after_interaction = before_interaction.copy()
                    after_interaction["clicked"] = True
                    after_interaction["success"] = True
                    
                    interactions.append(after_interaction)
                    
                    # 立即检查控制台日志，看是否触发了formStateManager
                    console_logs = self.driver.get_log('browser')
                    for log in console_logs[-5:]:  # 检查最近5条日志
                        if any(keyword in log['message'] for keyword in ['监听到表单选择', 'FIELD_CHANGE', '倒计时开始']):
                            self.logger.info(f"🎯 检测到表单状态变化日志: {log['message']}")
                    
                    # 等待并截图
                    time.sleep(2)
                    self.take_screenshot(f"after_option_click_q{i}")
                    
                    self.logger.info(f"✅ 题目 {i} 选择成功")
                    
                except NoSuchElementException:
                    self.logger.error(f"❌ 找不到选项元素: {option_id}")
                    continue
                except Exception as e:
                    self.logger.error(f"❌ 点击选项失败: {option_id} - {str(e)}")
                    continue
            
            # 记录所有交互
            self.test_session["form_clicks"].extend(interactions)
            
            if interactions:
                self.logger.info(f"✅ 表单交互完成，成功点击 {len(interactions)} 个选项")
                self.test_session["success_steps"].append(f"成功模拟 {len(interactions)} 个选项点击")
                
                # 等待可能的网络请求并监控10秒防抖机制
                self.logger.info("⏳ 等待10秒检查是否触发自动存储...")
                self.logger.info("🔍 开始监控formStateManager的10秒防抖倒计时...")
                
                # 分阶段检查防抖机制
                for countdown in [2, 5, 8, 12]:
                    time.sleep(countdown - (sum([2, 5, 8][:countdown//2]) if countdown > 2 else 0))
                    self.logger.info(f"⏱️ 防抖倒计时检查点: {countdown}秒")
                    
                    # 检查控制台中的防抖相关日志
                    try:
                        console_logs = self.driver.get_log('browser')
                        for log in console_logs[-10:]:
                            if any(keyword in log['message'] for keyword in ['倒计时', 'countdown', 'state_sync', 'SAVE', 'backend']):
                                self.logger.info(f"🎯 防抖机制日志: {log['message']}")
                    except Exception as log_error:
                        self.logger.debug(f"检查控制台日志时出错: {str(log_error)}")
                
                # 最终截图记录状态
                self.take_screenshot("after_10sec_debounce_wait")
                
                return True
            else:
                self.logger.error("❌ 没有成功点击任何选项")
                self.test_session["errors"].append("没有成功点击任何选项")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 表单交互模拟失败: {str(e)}")
            self.test_session["errors"].append(f"表单交互模拟失败: {str(e)}")
            return False
    
    def monitor_network_requests(self) -> List[Dict[str, Any]]:
        """
        监控和分析网络请求
        
        Returns:
            List[Dict[str, Any]]: 网络请求列表
        """
        self.logger.info("🌐 分析网络请求...")
        
        network_requests = []
        
        try:
            # 获取浏览器日志
            logs = self.driver.get_log('performance')
            
            for log in logs:
                message = json.loads(log['message'])
                if message['message']['method'] == 'Network.responseReceived':
                    response = message['message']['params']['response']
                    
                    request_info = {
                        "timestamp": log['timestamp'],
                        "url": response['url'],
                        "method": response.get('requestHeaders', {}).get(':method', 'unknown'),
                        "status": response['status'],
                        "statusText": response['statusText'],
                        "mimeType": response['mimeType']
                    }
                    
                    # 重点关注后端API请求
                    if self.backend_url in response['url'] or 'intent' in response['url'] or 'state_sync' in response['url']:
                        self.logger.info(f"🔍 发现API请求: {request_info['method']} {request_info['url']} - {request_info['status']}")
                        network_requests.append(request_info)
            
            # 记录网络请求
            self.test_session["network_requests"].extend(network_requests)
            
            if network_requests:
                self.logger.info(f"📊 监控到 {len(network_requests)} 个相关网络请求")
            else:
                self.logger.warning("⚠️ 没有监控到相关的API请求")
                self.test_session["errors"].append("没有监控到后端API请求")
            
            return network_requests
            
        except Exception as e:
            self.logger.error(f"❌ 网络请求监控失败: {str(e)}")
            self.test_session["errors"].append(f"网络请求监控失败: {str(e)}")
            return []
    
    def check_console_logs(self) -> List[Dict[str, Any]]:
        """
        检查浏览器控制台日志
        
        Returns:
            List[Dict[str, Any]]: 控制台日志列表
        """
        self.logger.info("📝 检查浏览器控制台日志...")
        
        console_logs = []
        
        try:
            logs = self.driver.get_log('browser')
            
            for log in logs:
                log_info = {
                    "timestamp": log['timestamp'],
                    "level": log['level'],
                    "message": log['message'],
                    "source": log.get('source', 'unknown')
                }
                
                # 重点关注formStateManager相关日志
                if any(keyword in log['message'] for keyword in [
                    'formStateManager', 'FIELD_CHANGE', 'state_sync', 'FORM_', '监听到表单选择', '倒计时'
                ]):
                    self.logger.info(f"📋 表单相关日志 [{log['level']}]: {log['message']}")
                    console_logs.append(log_info)
                elif log['level'] == 'SEVERE':
                    self.logger.error(f"🚨 严重错误日志: {log['message']}")
                    console_logs.append(log_info)
            
            if console_logs:
                self.logger.info(f"📊 检查到 {len(console_logs)} 条相关控制台日志")
            else:
                self.logger.warning("⚠️ 没有找到表单相关的控制台日志")
            
            return console_logs
            
        except Exception as e:
            self.logger.error(f"❌ 控制台日志检查失败: {str(e)}")
            return []
    
    def generate_analysis_report(self) -> Dict[str, Any]:
        """
        生成详细的分析报告
        
        Returns:
            Dict[str, Any]: 分析报告
        """
        self.logger.info("📊 生成分析报告...")
        
        end_time = datetime.now()
        duration = end_time - self.test_session["start_time"]
        
        report = {
            "test_session": {
                "start_time": self.test_session["start_time"].isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "form_id": self.test_session["form_id"]
            },
            "success_steps": self.test_session["success_steps"],
            "errors": self.test_session["errors"],
            "form_interactions": len(self.test_session["form_clicks"]),
            "network_requests": len(self.test_session["network_requests"]),
            "analysis": {
                "form_generated": bool(self.test_session["form_id"]),
                "interactions_successful": len(self.test_session["form_clicks"]) > 0,
                "api_requests_detected": len(self.test_session["network_requests"]) > 0,
                "test_passed": len(self.test_session["errors"]) == 0
            },
            "recommendations": []
        }
        
        # 生成建议
        if not report["analysis"]["form_generated"]:
            report["recommendations"].append("表单未生成 - 检查Take Test按钮点击逻辑和后端mbti_start处理器")
        
        if not report["analysis"]["interactions_successful"]:
            report["recommendations"].append("表单交互失败 - 检查表单元素选择器和事件绑定")
        
        if not report["analysis"]["api_requests_detected"]:
            report["recommendations"].append("未检测到API请求 - 检查formStateManager的state_sync机制和网络配置")
        
        if self.test_session["errors"]:
            report["recommendations"].append("存在错误 - 详细检查错误日志并修复相关问题")
        
        # 保存报告到文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.log_dir / f"analysis_report_{timestamp}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"📄 分析报告已保存: {report_file}")
        except Exception as e:
            self.logger.error(f"❌ 保存分析报告失败: {str(e)}")
        
        return report
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("🧹 清理资源...")
        
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("✅ 浏览器已关闭")
            except Exception as e:
                self.logger.error(f"❌ 关闭浏览器失败: {str(e)}")
    
    async def run_full_test(self) -> Dict[str, Any]:
        """
        运行完整的测试流程
        
        Returns:
            Dict[str, Any]: 测试报告
        """
        self.logger.info("🚀 开始MBTI表单自动化测试...")
        
        try:
            # 1. 检查服务状态
            services = self.check_services_status()
            if not services["frontend"]:
                self.logger.error("❌ 前端服务不可用，测试终止")
                return self.generate_analysis_report()
            
            # 2. 配置浏览器
            if not self.setup_chrome_driver():
                return self.generate_analysis_report()
            
            # 3. 导航到前端
            if not self.navigate_to_frontend():
                return self.generate_analysis_report()
            
            # 4. 先点击Personality Assessment按钮
            if not self.click_personality_assessment():
                return self.generate_analysis_report()
            
            # 5. 检查是否需要登录
            if not self.handle_login_requirement():
                return self.generate_analysis_report()
            
            # 6. 再点击Take Test按钮
            if not self.click_take_test_button():
                return self.generate_analysis_report()
            
            # 7. 等待表单生成
            form_id = self.wait_for_form_generation()
            if not form_id:
                return self.generate_analysis_report()
            
            # 8. 分析表单结构
            analysis = self.analyze_form_structure(form_id)
            if not analysis["structure_valid"]:
                self.logger.error("❌ 表单结构无效")
                return self.generate_analysis_report()
            
            # 9. 模拟表单交互（关键测试：验证10秒防抖机制）
            if not self.simulate_form_interaction(form_id, analysis):
                return self.generate_analysis_report()
            
            # 10. 监控网络请求（分析state_sync请求）
            self.monitor_network_requests()
            
            # 11. 检查控制台日志（分析formStateManager日志）
            self.check_console_logs()
            
            # 12. 生成详细分析报告
            return self.generate_analysis_report()
            
        except Exception as e:
            self.logger.error(f"❌ 测试过程中发生异常: {str(e)}")
            self.test_session["errors"].append(f"测试异常: {str(e)}")
            return self.generate_analysis_report()
        
        finally:
            self.cleanup()


async def main():
    """主函数"""
    print("🧪 MBTI表单自动化测试开始...")
    print("=" * 60)
    
    # 创建测试器实例
    tester = MBTIFormTester()
    
    # 运行测试
    report = await tester.run_full_test()
    
    # 输出测试结果总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结:")
    print(f"✅ 成功步骤: {len(report['success_steps'])}")
    print(f"❌ 错误数量: {len(report['errors'])}")
    print(f"🎯 表单交互: {report['form_interactions']} 次")
    print(f"🌐 网络请求: {report['network_requests']} 个")
    print(f"📋 测试通过: {'✅ 是' if report['analysis']['test_passed'] else '❌ 否'}")
    
    if report['recommendations']:
        print("\n💡 建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    print("=" * 60)
    print("🏁 测试完成！详细日志请查看 cry_frontend/test/logs/ 目录")


if __name__ == "__main__":
    asyncio.run(main())
