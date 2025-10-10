# BulkMail.py 实际使用示例

## 🎯 立即可用的命令

### 基础使用
```bash
# 进入后端目录并激活虚拟环境
cd cry_backend
source venv/bin/activate

# 使用测试邮箱文件发送验证码邮件
python utilities/mail/BulkMail.py utilities/mail/test_emails.txt verification --subject "您的验证码"
```

### 自定义参数
```bash
# 小批次快速发送
python utilities/mail/BulkMail.py emails.txt verification --subject "紧急验证码" --batch-size 5 --delay 0.5

# 大批次慢速发送  
python utilities/mail/BulkMail.py marketing_list.txt marketing --subject "特惠活动" --batch-size 25 --delay 3.0

# 指定日志文件
python utilities/mail/BulkMail.py users.txt welcome --subject "欢迎" --log-file custom_send.log
```

## 📋 邮箱文件准备

### 创建您的邮箱文件
```bash
# 创建一个包含100个邮箱的文件
cat > my_emails.txt << EOF
user1@example.com
user2@example.com
user3@example.com
# ... 添加更多邮箱地址
user100@example.com
EOF
```

### 使用您的邮箱文件
```bash
python utilities/mail/BulkMail.py my_emails.txt verification --subject "重要验证码"
```

## 🔄 断点续传演示

### 场景1: 正常中断恢复
```bash
# 1. 启动批量发送（假设发送50封后按CTRL+C中断）
python utilities/mail/BulkMail.py large_list.txt welcome --subject "欢迎邮件"

# 输出: 🛑 检测到中断信号，正在安全停止...
#       ✅ 会话已保存，可使用断点续传恢复

# 2. 再次运行相同命令，系统自动检测
python utilities/mail/BulkMail.py large_list.txt welcome --subject "欢迎邮件"

# 输出: 🔄 检测到 1 个未完成的邮件发送任务:
#       1. 模板: welcome | 邮件文件: large_list.txt | 剩余: 50/100
#       请选择操作: r) 恢复 s) 跳过 c) 取消

# 3. 选择 'r' 自动从第51封邮件继续发送
```

### 场景2: 强制恢复
```bash
# 跳过交互，直接恢复所有未完成任务
python utilities/mail/BulkMail.py any_file.txt any_template --subject "任意" --resume
```

## 📊 实际运行效果

### 成功运行示例
```
🔍 检测未完成的邮件发送任务...
✅ 没有检测到未完成任务，开始新任务

🚀 开始新的邮件发送任务
📁 邮件文件: test_emails.txt
🎨 模板: verification
📧 主题: 测试邮件
📊 邮件总数: 10

📦 分为 4 个批次，每批 3 封邮件

📬 处理批次 1/4 (3 封邮件)
发送邮件: 30%|███       | 3/10 [00:01<00:03, 2.1封/s, success=3, failed=0, rate=100.0%]
⏳ 等待 1.0 秒后继续下一批次...

📬 处理批次 2/4 (3 封邮件)  
发送邮件: 60%|██████    | 6/10 [00:03<00:02, 2.0封/s, success=6, failed=0, rate=100.0%]

...

📊 发送完成统计:
✅ 成功: 10
❌ 失败: 0  
📈 成功率: 100.0%

🎉 所有邮件发送任务完成！
```

### 有失败的运行示例
```
📬 处理批次 2/4 (3 封邮件)
发送邮件: 50%|█████     | 5/10 [00:02<00:02, 1.8封/s, success=4, failed=1, rate=80.0%]

📊 发送完成统计:
✅ 成功: 8
❌ 失败: 2
📈 成功率: 80.0%

📝 失败详情已记录到日志文件: utilities/mail/logs/bulk_20240919_153000.log
```

## 📄 日志文件查看

### 查看发送日志
```bash
# 查看最新的日志文件
ls -la utilities/mail/logs/

# 查看日志内容
cat utilities/mail/logs/bulk_20240919_153000.log

# 实时监控日志（另开终端）
tail -f utilities/mail/logs/bulk_20240919_153000.log
```

### 日志文件内容示例
```
[SESSION_START] 2024-09-19T15:30:00 | SessionID: bulk_20240919_153000 | EmailFile: test_emails.txt | Template: verification | Subject: 测试邮件 | Total: 10

[PROGRESS] user1@test.local | SUCCESS | 2024-09-19T15:30:01
[PROGRESS] user2@test.local | SUCCESS | 2024-09-19T15:30:02
[PROGRESS] user3@test.local | FAILED | SMTPConnectError: [Errno 111] Connection refused | 2024-09-19T15:30:03

[BATCH] Batch 1/4 completed | Success: 2/3 | 2024-09-19T15:30:05

[SESSION_END] 2024-09-19T15:35:00 | SessionID: bulk_20240919_153000 | Status: COMPLETED | Success: 8/10 | Failed: 2 | Rate: 80.0%
```

## 🛠️ 维护命令

### 清理旧日志
```bash
# 清理7天前的日志
python utilities/mail/BulkMail.py --clean-logs 7

# 清理30天前的日志
python utilities/mail/BulkMail.py --clean-logs 30
```

### 查看帮助
```bash
python utilities/mail/BulkMail.py --help
```

## 🎯 您的实际使用场景

### 步骤1: 准备邮箱文件
```bash
# 将您的100个邮箱地址保存到文件中
nano my_100_emails.txt
# 每行一个邮箱地址，保存文件
```

### 步骤2: 执行批量发送
```bash
# 发送验证码邮件给100个用户
python utilities/mail/BulkMail.py my_100_emails.txt verification --subject "您的账户验证码"

# 或发送营销邮件
python utilities/mail/BulkMail.py my_100_emails.txt marketing --subject "Career Bot 新功能上线"
```

### 步骤3: 监控发送过程
- 观察实时进度条
- 注意成功率和失败统计
- 如需中断可按CTRL+C安全停止

### 步骤4: 处理中断恢复
```bash
# 如果发送被中断，再次运行相同命令
python utilities/mail/BulkMail.py my_100_emails.txt verification --subject "您的账户验证码"

# 选择 'r' 继续发送剩余邮件
```

现在您就可以轻松处理100个邮箱地址的批量发送了！🚀
