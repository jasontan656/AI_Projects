#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
点击Personality Assessment后的页面变化调试脚本
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def debug_after_personality_click():
    """调试点击Personality Assessment后的页面变化"""
    print("🔍 调试点击后的页面变化...")
    
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
        
        print("📸 点击前的页面状态:")
        print(f"  页面标题: {driver.title}")
        print(f"  当前URL: {driver.current_url}")
        
        # 点击Personality Assessment
        print("\n🖱️ 点击 Start personality assessment...")
        assessment_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@class='group-link group-link--DevComplete']"))
        )
        assessment_link.click()
        print("✅ 点击成功")
        
        # 等待并观察变化
        for i in range(10):
            time.sleep(2)
            print(f"\n📸 点击后 {(i+1)*2} 秒的状态:")
            print(f"  当前URL: {driver.current_url}")
            
            # 查找所有新出现的按钮
            buttons = driver.find_elements(By.TAG_NAME, "button")
            print(f"  按钮数量: {len(buttons)}")
            for j, btn in enumerate(buttons):
                text = btn.text.strip()
                if text and ('take' in text.lower() or 'test' in text.lower()):
                    print(f"    按钮 {j+1}: '{text}' - ID: '{btn.get_attribute('id')}' - Class: '{btn.get_attribute('class')}'")
            
            # 查找所有新出现的链接
            links = driver.find_elements(By.TAG_NAME, "a")
            print(f"  链接数量: {len(links)}")
            for j, link in enumerate(links):
                text = link.text.strip()
                if text and ('take' in text.lower() or 'test' in text.lower()):
                    print(f"    链接 {j+1}: '{text}' - href: '{link.get_attribute('href')}' - Class: '{link.get_attribute('class')}'")
            
            # 检查是否有表单出现
            forms = driver.find_elements(By.XPATH, "//div[contains(@class, 'form') or contains(@id, 'form')]")
            if forms:
                print(f"  发现表单元素: {len(forms)} 个")
                for k, form in enumerate(forms):
                    print(f"    表单 {k+1}: ID='{form.get_attribute('id')}', Class='{form.get_attribute('class')}'")
            
            # 检查消息泡泡中是否有新内容
            messages = driver.find_elements(By.CSS_SELECTOR, ".message-bubble")
            print(f"  消息泡泡数量: {len(messages)}")
            
            # 如果找到了Take Test相关的元素就停止
            all_text = driver.page_source.lower()
            if 'take test' in all_text:
                print("🎯 发现 'Take Test' 相关内容!")
                break
        
        # 最终状态检查
        print("\n🔍 最终页面内容检查:")
        all_clickable = driver.find_elements(By.XPATH, "//*[self::button or self::a or @onclick or contains(@class, 'clickable') or contains(@class, 'btn')]")
        for element in all_clickable:
            text = element.text.strip()
            if text and len(text) < 100:  # 只显示短文本
                tag = element.tag_name
                onclick = element.get_attribute('onclick')
                data_intent = element.get_attribute('data-intent')
                print(f"  {tag}: '{text}' - onclick: {onclick} - data-intent: {data_intent}")
        
        # 保存最终页面源码
        with open("page_after_click.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("\n💾 点击后的页面源码已保存到 page_after_click.html")
        
    except Exception as e:
        print(f"❌ 调试过程出错: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        input("\n按回车键关闭浏览器...")  # 暂停让我们能看到浏览器状态
        driver.quit()
        print("🏁 调试完成")


if __name__ == "__main__":
    debug_after_personality_click()
