# Career Bot 邮件系统使用指南

## 概述

本邮件系统支持传统邮件发送、模板邮件和批量群发功能，满足各种邮件发送需求。

## 功能特性

- 🔧 **传统邮件发送** - 向下兼容现有代码
- 🎨 **模板邮件系统** - 支持HTML/文本模板，动态变量替换
- 📬 **批量群发功能** - 高效处理大量邮件发送
- ⚡ **异步并发处理** - 提高发送效率
- 🛡️ **发送限制保护** - 防止触发邮件服务商限制
- 📊 **详细发送统计** - 成功率、失败统计和错误跟踪

## 安装依赖

```bash
pip install jinja2>=3.1.0
```

## 基础使用

### 1. 传统邮件发送（保持兼容）

```python
from shared_utilities.mail import send_email

# 发送纯文本邮件
result = await send_email(
    to="user@example.com",
    subject="测试邮件",
    body="这是一封测试邮件",
    content_type="plain"
)

# 发送HTML邮件
result = await send_email(
    to=["user1@example.com", "user2@example.com"],
    subject="HTML邮件",
    body="<h1>欢迎使用Career Bot</h1><p>这是一封HTML邮件</p>",
    content_type="html"
)
```

### 2. 模板邮件发送

```python
from shared_utilities.mail import send_template_email

# 发送验证码邮件
result = await send_template_email(
    to="user@example.com",
    subject="邮箱验证码",
    template_name="verification",
    template_vars={
        "verification_code": "123456",
        "expiry_minutes": 5,
        "is_test_mode": False
    }
)

# 发送欢迎邮件
result = await send_template_email(
    to="newuser@example.com",
    subject="欢迎加入Career Bot",
    template_name="welcome",
    template_vars={
        "user_name": "张三",
        "dashboard_link": "https://careerbot.com/dashboard",
        "next_steps": [
            "完善个人资料",
            "进行MBTI测试",
            "上传简历"
        ]
    }
)
```

### 3. 营销邮件发送

```python
# 发送营销推广邮件
result = await send_template_email(
    to=["user1@example.com", "user2@example.com"],
    subject="Career Bot 最新功能上线",
    template_name="marketing",
    template_vars={
        "user_name": "用户",
        "campaign_name": "新功能发布",
        "featured_content": {
            "title": "AI简历优化功能",
            "description": "使用人工智能技术优化您的简历",
            "link": "https://careerbot.com/resume-ai"
        },
        "content_items": [
            {"title": "智能匹配", "description": "更精准的职位推荐"},
            {"title": "面试指导", "description": "AI驱动的面试准备"}
        ],
        "cta_button": {
            "text": "立即体验",
            "link": "https://careerbot.com/features"
        }
    }
)
```

## 批量群发功能

### 1. 批量发送相同内容

```python
from shared_utilities.mail import send_bulk_email

# 准备收件人列表（支持100+邮箱）
recipients = [
    "user1@example.com",
    "user2@example.com",
    "user3@example.com",
    # ... 更多邮箱地址
]

# 批量发送
result = await send_bulk_email(
    recipients=recipients,
    subject="重要通知 - 系统维护",
    body="尊敬的用户，系统将于今晚进行维护...",
    content_type="plain",
    batch_size=20,  # 每批发送20封
    delay_between_batches=2.0  # 批次间延迟2秒
)

# 查看发送统计
print(f"总计邮件: {result['total_recipients']}")
print(f"成功发送: {result['success_count']}")
print(f"发送失败: {result['failed_count']}")
print(f"成功率: {result['success_rate']:.2f}%")
print(f"失败列表: {result['failed_recipients']}")
```

### 2. 批量发送个性化模板邮件

```python
from shared_utilities.mail import send_bulk_template_email

# 准备个性化收件人数据
recipients = [
    {
        "email": "zhang@example.com",
        "vars": {
            "user_name": "张三",
            "verification_code": "123456",
            "expiry_minutes": 5
        }
    },
    {
        "email": "li@example.com", 
        "vars": {
            "user_name": "李四",
            "verification_code": "789012",
            "expiry_minutes": 5
        }
    },
    # ... 更多个性化数据
]

# 批量发送个性化邮件
result = await send_bulk_template_email(
    recipients=recipients,
    subject="您的验证码",
    template_name="verification",
    content_type="html",
    batch_size=15,
    delay_between_batches=1.5
)
```

### 3. 营销活动批量发送

```python
# 营销活动的收件人数据
marketing_recipients = [
    {
        "email": "premium@example.com",
        "vars": {
            "user_name": "王总",
            "campaign_name": "VIP专享优惠",
            "featured_content": {
                "title": "高端职业咨询服务",
                "description": "一对一专业职业规划师服务"
            }
        }
    },
    {
        "email": "student@example.com",
        "vars": {
            "user_name": "小李",
            "campaign_name": "学生专属福利",
            "featured_content": {
                "title": "校园招聘特训营",
                "description": "提升求职竞争力"
            }
        }
    }
]

# 批量发送营销邮件
result = await send_bulk_template_email(
    recipients=marketing_recipients,
    subject="专属优惠 - Career Bot",
    template_name="marketing",
    batch_size=10,
    delay_between_batches=3.0  # 营销邮件间隔长一些
)
```

## 模板管理

### 可用模板

- `verification` - 验证码邮件（HTML + 纯文本版本）
- `welcome` - 欢迎邮件 
- `marketing` - 营销推广邮件
- `base` - 基础HTML布局模板

### 模板变量

#### 验证码模板变量
- `verification_code` - 验证码
- `expiry_minutes` - 有效期分钟数
- `is_test_mode` - 是否测试模式

#### 欢迎邮件变量
- `user_name` - 用户姓名
- `dashboard_link` - 仪表板链接
- `next_steps` - 后续步骤列表

#### 营销邮件变量
- `user_name` - 用户姓名
- `campaign_name` - 活动名称
- `featured_content` - 特色内容对象
- `content_items` - 内容项目列表
- `cta_button` - 行动按钮对象

### 检查模板可用性

```python
from shared_utilities.mail import mail_template_manager

# 检查模板是否存在
exists = mail_template_manager.template_exists("verification", "html")

# 获取所有可用模板
templates = mail_template_manager.get_available_templates()
print(f"HTML模板: {templates['html']}")
print(f"文本模板: {templates['plain']}")
```

## 最佳实践

### 1. 批量发送设置

```python
# 小批量高频发送（验证码等紧急邮件）
batch_size = 5
delay_between_batches = 0.5

# 中批量中频发送（通知类邮件）
batch_size = 20
delay_between_batches = 2.0

# 大批量低频发送（营销邮件）
batch_size = 50
delay_between_batches = 5.0
```

### 2. 错误处理

```python
try:
    result = await send_bulk_template_email(
        recipients=recipients,
        subject="测试邮件",
        template_name="verification"
    )
    
    if result['failed_count'] > 0:
        print(f"部分发送失败: {result['failed_recipients']}")
        # 可以选择重试失败的邮件
        
except Exception as e:
    print(f"批量发送失败: {e}")
```

### 3. 性能优化

```python
# 对于超大批量（1000+邮件），建议分多次执行
async def send_large_batch(all_recipients, **kwargs):
    chunk_size = 200  # 每次处理200个
    
    for i in range(0, len(all_recipients), chunk_size):
        chunk = all_recipients[i:i+chunk_size]
        
        result = await send_bulk_template_email(
            recipients=chunk,
            **kwargs
        )
        
        print(f"批次 {i//chunk_size + 1} 完成")
        await asyncio.sleep(10)  # 批次间休息10秒
```

## 注意事项

1. **发送限制**: 遵循邮件服务商的发送限制，合理设置批次大小和延迟
2. **模板路径**: 模板文件位于 `utilities/mail/templates/` 目录
3. **向下兼容**: 现有 `send_email` 函数完全兼容旧代码
4. **错误恢复**: 批量发送中单个邮件失败不会影响其他邮件
5. **内容类型**: HTML模板默认使用 `content_type="html"`，纯文本使用 `"plain"`

## 故障排除

### 模板渲染失败
- 检查模板文件是否存在
- 确认模板变量名称正确
- 查看模板语法是否正确

### 批量发送性能问题
- 减小 batch_size
- 增加 delay_between_batches
- 检查网络连接和SMTP服务器响应

### 发送失败率高
- 检查收件人邮箱地址格式
- 确认SMTP服务器配置
- 查看邮件内容是否触发垃圾邮件过滤器
