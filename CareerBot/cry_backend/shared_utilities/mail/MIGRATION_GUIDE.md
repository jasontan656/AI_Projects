# 邮件系统升级迁移指南

## 概述

本指南帮助您将现有的邮件发送代码升级到新的模板和批量发送系统。

## 现有代码兼容性

✅ **完全兼容** - 现有的 `send_email` 函数调用无需修改，可以正常工作。

## 认证模块升级示例

### 原有代码（email_verification.py）

```python
# 当前的验证码邮件发送方式
from shared_utilities.mail.SendMail import send_email

# 组织邮件主题和正文内容
subject = "邮箱验证码 - 验证您的身份"
if is_test_user:
    body = f"您的验证码是：{code}\n\n这是测试验证码，验证码有效期为5分钟，请及时使用。\n注意：这是开发测试模式。"
else:
    body = f"您的验证码是：{code}\n\n验证码有效期为5分钟，请及时使用。"

return await send_email(
    to=email,
    subject=subject,
    body=body,
    content_type="plain"
)
```

### 升级后的代码（推荐方式）

```python
# 使用模板的验证码邮件发送方式
from shared_utilities.mail import send_template_email

# 直接使用模板发送，自动处理HTML格式和样式
return await send_template_email(
    to=email,
    subject="邮箱验证码 - 验证您的身份",
    template_name="verification",
    template_vars={
        "verification_code": code,
        "expiry_minutes": 5,
        "is_test_mode": is_test_user,
        "send_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    },
    content_type="html"  # 使用美观的HTML格式
)
```

### 密码重置邮件升级

```python
# 原有方式
subject = "密码重置验证码 - 重置您的账户密码"
body = f"您的密码重置验证码是：{code}\n\n验证码有效期为10分钟，请及时使用。"

# 升级方式 - 创建密码重置模板
return await send_template_email(
    to=email,
    subject="密码重置验证码 - 重置您的账户密码", 
    template_name="password_reset",  # 需要创建此模板
    template_vars={
        "verification_code": code,
        "expiry_minutes": 10,
        "is_test_mode": is_test_user
    }
)
```

## 批量发送场景示例

### 系统通知群发

```python
from shared_utilities.mail import send_bulk_template_email

# 向所有活跃用户发送系统维护通知
active_users = [
    {"email": "user1@example.com", "vars": {"user_name": "张三"}},
    {"email": "user2@example.com", "vars": {"user_name": "李四"}},
    # ... 更多用户
]

result = await send_bulk_template_email(
    recipients=active_users,
    subject="系统维护通知 - Career Bot",
    template_name="system_notification",  # 需要创建此模板
    batch_size=25,
    delay_between_batches=2.0
)

print(f"通知发送完成，成功率: {result['success_rate']:.1f}%")
```

### 营销活动推广

```python
# 向注册用户推送新功能介绍
marketing_data = [
    {
        "email": "premium@example.com",
        "vars": {
            "user_name": "王总",
            "user_tier": "VIP",
            "featured_content": {
                "title": "VIP专属简历优化",
                "description": "人工智能驱动的高端简历定制服务"
            }
        }
    }
    # ... 更多用户数据
]

await send_bulk_template_email(
    recipients=marketing_data,
    subject="Career Bot 新功能上线 - 专为您定制",
    template_name="marketing",
    batch_size=15,
    delay_between_batches=3.0
)
```

## 渐进式迁移策略

### 阶段1: 保持现有功能
- 现有代码无需修改，继续使用 `send_email`
- 新功能开发时使用模板系统

### 阶段2: 逐步替换高频邮件
- 优先升级验证码、密码重置等高频邮件
- 创建对应的邮件模板
- 逐步替换函数调用

### 阶段3: 批量功能应用
- 识别需要群发的场景
- 实现营销推广、系统通知等批量发送
- 优化发送策略和模板

## 模板创建指南

### 创建新模板文件

1. **HTML模板**: 在 `utilities/mail/templates/` 目录创建 `.html` 文件
2. **纯文本模板**: 在 `utilities/mail/templates/plain/` 目录创建 `.txt` 文件

### 密码重置模板示例

创建 `utilities/mail/templates/password_reset.html`:

```html
{% extends "base.html" %}

{% block header %}密码重置验证码{% endblock %}

{% block content %}
<p>亲爱的用户：</p>

<p>您正在进行密码重置，您的验证码是：</p>

<div style="text-align: center; margin: 30px 0;">
    <span style="font-size: 32px; font-weight: bold; color: #dc2626; 
                 background-color: #fef2f2; padding: 15px 25px; 
                 border-radius: 8px; letter-spacing: 4px;">
        {{ verification_code }}
    </span>
</div>

<p><strong>重要提醒：</strong></p>
<ul>
    <li>验证码有效期为 <span class="highlight">{{ expiry_minutes }} 分钟</span></li>
    <li>如果您没有申请重置密码，请忽略此邮件</li>
    <li>为了您的账户安全，请勿将验证码泄露给他人</li>
</ul>
{% endblock %}
```

## 性能优化建议

### 批量发送参数调优

```python
# 验证码等紧急邮件（快速发送）
batch_size = 5
delay_between_batches = 0.5

# 系统通知（平衡发送）  
batch_size = 20
delay_between_batches = 2.0

# 营销邮件（慢速发送，避免被标记为垃圾邮件）
batch_size = 10
delay_between_batches = 5.0
```

### 错误处理和重试

```python
async def send_with_retry(recipients, **kwargs):
    max_retries = 3
    
    for attempt in range(max_retries):
        result = await send_bulk_template_email(
            recipients=recipients,
            **kwargs
        )
        
        if result['success_rate'] > 95:  # 成功率超过95%认为成功
            return result
            
        # 重试失败的收件人
        recipients = [
            {"email": email, "vars": kwargs.get('template_vars', {})}
            for email in result['failed_recipients']
        ]
        
        if not recipients:
            break
            
        print(f"重试第 {attempt + 1} 次，剩余 {len(recipients)} 个收件人")
        await asyncio.sleep(10)  # 重试前等待
        
    return result
```

## 注意事项

1. **模板变量验证**: 确保传入的模板变量与模板中使用的变量匹配
2. **批量发送监控**: 监控批量发送的成功率，及时调整参数
3. **邮件内容合规**: 确保邮件内容符合反垃圾邮件规定
4. **测试环境隔离**: 在测试环境中充分测试批量发送功能

## 故障排除

### 常见问题

1. **模板渲染失败**: 检查模板语法和变量名
2. **批量发送超时**: 减小批次大小，增加延迟时间
3. **邮件被拒收**: 检查发送频率，调整内容格式

### 日志和调试

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 发送时查看详细信息
result = await send_bulk_template_email(...)
print(f"发送详情: {result}")
```
