#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页面内容调试脚本
用于分析页面上的所有按钮和可点击元素，帮助找到正确的选择器
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def debug_page_content():
    """分析页面内容，找出所有可点击元素"""
    print("🔍 页面内容调试开始...")
    
    # 配置Chrome
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # 访问前端页面
        url = "http://localhost:5173"
        print(f"🌐 访问: {url}")
        driver.get(url)
        time.sleep(3)
        
        print(f"📄 页面标题: {driver.title}")
        print(f"🔗 当前URL: {driver.current_url}")
        
        # 查找所有按钮
        print("\n🔘 所有按钮元素:")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for i, button in enumerate(buttons):
            print(f"  {i+1}. 按钮文本: '{button.text.strip()}'")
            print(f"     ID: '{button.get_attribute('id')}'")
            print(f"     Class: '{button.get_attribute('class')}'")
            print(f"     数据属性: {[attr for attr in button.get_property('attributes') if 'data-' in str(attr)]}")
            print()
        
        # 查找所有链接
        print("🔗 所有链接元素:")
        links = driver.find_elements(By.TAG_NAME, "a")
        for i, link in enumerate(links):
            text = link.text.strip()
            if text:  # 只显示有文本的链接
                print(f"  {i+1}. 链接文本: '{text}'")
                print(f"     href: '{link.get_attribute('href')}'")
                print(f"     Class: '{link.get_attribute('class')}'")
                print()
        
        # 查找包含特定关键词的元素
        print("🎯 包含关键词的元素:")
        all_elements = driver.find_elements(By.XPATH, "//*")
        keywords = ['personality', 'assessment', 'mbti', 'take', 'test', '性格', '测评']
        
        for element in all_elements:
            text = element.text.strip().lower()
            if any(keyword in text for keyword in keywords):
                print(f"  标签: {element.tag_name}")
                print(f"  文本: '{element.text.strip()}'")
                print(f"  ID: '{element.get_attribute('id')}'")
                print(f"  Class: '{element.get_attribute('class')}'")
                print(f"  可点击: {element.is_enabled()}")
                print()
        
        # 保存页面源码用于分析
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("💾 页面源码已保存到 page_source.html")
        
    except Exception as e:
        print(f"❌ 调试过程出错: {str(e)}")
    finally:
        driver.quit()
        print("🏁 调试完成")


if __name__ == "__main__":
    debug_page_content()
