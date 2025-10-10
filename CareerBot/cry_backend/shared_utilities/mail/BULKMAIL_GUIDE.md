# BulkMail.py 批量邮件发送工具使用指南

## 🎯 功能特性

- ✅ **命令行操作** - 简单的命令行接口，一键批量发送
- ✅ **进度显示** - 实时进度条和发送状态
- ✅ **详细日志** - 记录每封邮件的发送结果和错误信息  
- ✅ **断点续传** - 智能检测未完成任务，支持恢复发送
- ✅ **用户交互** - 友好的用户询问和选择界面
- ✅ **模板支持** - 使用HTML邮件模板，美观专业
- ✅ **错误处理** - 详细的SMTP错误信息记录

## 🚀 快速开始

### 安装依赖
```bash
cd cry_backend
source venv/bin/activate
pip install tqdm>=4.65.0
```

### 基本使用
```bash
# 发送验证码邮件给100个用户
python utilities/mail/BulkMail.py emails.txt verification --subject "您的验证码"

# 发送欢迎邮件，自定义批次大小
python utilities/mail/BulkMail.py users.txt welcome --subject "欢迎加入Career Bot" --batch-size 20

# 发送营销邮件，较长延迟
python utilities/mail/BulkMail.py vip_users.txt marketing --subject "VIP专属优惠" --delay 5.0

# 发送带附件的邮件
python utilities/mail/BulkMail.py emails.txt verification --subject "重要文件" --attachments-dir utilities/mail/attachments
```
source venv/bin/activate && python utilities/mail/BulkMail.py utilities/mail/test_emails.txt office --subject "Company Restructuring - Complete Office & Equipment Liquidation Sale" --attachments-dir utilities/mail/attachments


## 📁 邮箱文件格式

### 支持的格式

**纯邮箱列表（推荐）：**
```
user1@example.com
user2@example.com
user3@example.com
```

**CSV格式：**
```
张三,user1@example.com
李四,user2@example.com
```

**带注释：**
```
user1@example.com  # VIP用户
user2@example.com  # 普通用户
# 这是注释行，会被忽略
user3@example.com
```

## 📎 附件功能

### 全局附件发送

系统支持为所有邮件自动附加相同的附件文件，适用于产品手册、合同文档、软件包等场景。

**命令行参数：**
```bash
--attachments-dir <目录路径>
-a <目录路径>             # 短参数形式
```

### 使用方法

**基本用法：**
```bash
# 发送带附件的邮件
python utilities/mail/BulkMail.py emails.txt verification \
  --subject "重要文件分享" \
  --attachments-dir utilities/mail/attachments
```

**推荐文件夹结构：**
```
utilities/mail/attachments/
├── company_logo.png          # 公司标志 (< 1MB)
├── user_manual.pdf           # 用户手册 (2-5MB)  
├── software_package.zip      # 软件包 (10-30MB)
└── product_brochure.pdf      # 产品介绍 (1-3MB)
```

### 支持的文件格式

**文档类型：** PDF, Word (.doc/.docx), 文本 (.txt/.rtf)  
**压缩包：** ZIP, RAR, 7-Zip  
**图片类型：** JPG, PNG, GIF, BMP, TIFF  
**办公文档：** Excel (.xlsx/.xls), PowerPoint (.pptx/.ppt)

### 智能优化功能

系统会根据附件大小自动调整发送参数：

- **小附件 (≤5MB)：** 保持原始参数，预计5-10分钟
- **中等附件 (5-20MB)：** 批次大小减半，延迟翻倍，预计15-30分钟  
- **大附件 (>20MB)：** 批次大小降至3封，延迟8秒+，预计45-90分钟

### 实际使用示例

**产品发布邮件：**
```bash
# 准备附件文件夹
mkdir -p utilities/mail/attachments/product_release
cp software_v2.0.zip utilities/mail/attachments/product_release/
cp release_notes.pdf utilities/mail/attachments/product_release/

# 发送产品发布邮件
python utilities/mail/BulkMail.py customer_list.txt marketing \
  --subject "产品v2.0正式发布" \
  --attachments-dir utilities/mail/attachments/product_release
```

**技术支持邮件：**
```bash
# 准备技术文档
cp troubleshooting.pdf utilities/mail/attachments/
cp software_patch.zip utilities/mail/attachments/

# 发送支持邮件
python utilities/mail/BulkMail.py support_users.txt verification \
  --subject "技术支持资料" \
  --attachments-dir utilities/mail/attachments
```

### 附件发送过程

**扫描阶段：**
```
📎 处理附件...
📂 扫描附件文件夹: utilities/mail/attachments
   ✅ user_manual.pdf (2.3MB)
   ✅ software_v2.zip (28.5MB)
   🏷️  user_manual.pdf: application/pdf
   🏷️  software_v2.zip: application/zip
📊 共发现 2 个附件，总大小: 30.8MB
⏭️  跳过文件: .DS_Store, README.md

🔧 基于附件大小(30.8MB)自动调整发送参数:
   批次大小: 15 → 3
   批次延迟: 2.0 → 8.0秒
   预计发送时间: 45-90分钟
✅ 自动使用推荐参数优化发送性能
```

**发送阶段：**
```
📬 处理批次 1/34 (3 封邮件)
✅ Email with 2 attachments sent successfully to user1@example.com
✅ Email with 2 attachments sent successfully to user2@example.com
⚠️  Email with 2 attachments failed: SMTPDataError: Message too large
发送邮件: 9%|▉         | 3/100 [03:45<38:20, success=2, failed=1, rate=66.7%]
```

### 注意事项

**文件大小限制：**
- Gmail: 25MB总限制  
- Outlook: 20MB总限制
- 企业邮件: 通常10-25MB限制
- 系统在>20MB时显示警告但不阻止发送

**自动跳过的文件：**
- 临时文件: `.tmp`, `.temp`, `.cache`
- 系统文件: `.DS_Store`, `Thumbs.db`  
- 文档文件: `.md`, `.gitkeep`
- 备份文件: `.bak`, `.backup`, `~`开头

**性能影响：**
- 带附件邮件发送时间显著增加
- 大附件会自动调整为小批次发送
- 网络上传速度影响总体发送时间

## 🔄 断点续传功能

### 自动检测
运行工具时会自动检测未完成的任务：

```bash
$ python utilities/mail/BulkMail.py emails.txt verification --subject "测试"

🔍 检测未完成的邮件发送任务...

🔄 检测到 1 个未完成的邮件发送任务:
  1. 模板: verification | 邮件文件: emails.txt | 剩余: 45/100 | 开始时间: 2024-09-19 15:30:00

请选择操作:
  r) 恢复并完成所有未完成任务
  s) 跳过未完成任务，开始新任务  
  c) 取消操作

请输入选择 (r/s/c): r
```

### 强制恢复
```bash
# 跳过交互，自动恢复
python utilities/mail/BulkMail.py emails.txt verification --subject "测试" --resume
```

## 📊 进度显示

### 实时进度条
```
发送邮件: 45%|████▌     | 45/100 [00:32<00:23, 2.34封/s, success=42, failed=3, rate=93.3%]
```

### 批次进度
```
📦 分为 5 个批次，每批 20 封邮件

📬 处理批次 1/5 (20 封邮件)
📬 处理批次 2/5 (20 封邮件)
⏳ 等待 2.0 秒后继续下一批次...
```

## 📝 日志文件

### 日志格式
```
[SESSION_START] 2024-09-19T15:30:00 | SessionID: bulk_20240919_153000 | EmailFile: emails.txt | Template: verification | Subject: 您的验证码 | Total: 100

[PROGRESS] user1@example.com | SUCCESS | 2024-09-19T15:30:01
[PROGRESS] user2@example.com | FAILED | SMTPServerDisconnected: Connection lost | 2024-09-19T15:30:02
[PROGRESS] user3@example.com | SUCCESS | 2024-09-19T15:30:03

[BATCH] Batch 1/5 completed | Success: 18/20 | 2024-09-19T15:30:15

[SESSION_END] 2024-09-19T15:35:00 | SessionID: bulk_20240919_153000 | Status: COMPLETED | Success: 95/100 | Failed: 5 | Rate: 95.0%
```

### 日志文件位置
- 默认位置: `utilities/mail/logs/bulk_YYYYMMDD_HHMMSS.log`
- 自定义位置: `--log-file /path/to/custom.log`

## 📋 完整参数说明

### 命令行参数详细说明

```bash
python utilities/mail/BulkMail.py <邮箱文件> <模板名> [选项...]
```

**必需参数：**
- `email_file` - 包含邮箱地址的文本文件路径
- `template` - 邮件模板名称 (verification, welcome, marketing)
- `--subject/-s` - 邮件主题（必需）

**可选参数：**
- `--batch-size/-b <数量>` - 每批发送邮件数量（默认：15）
- `--delay/-d <秒数>` - 批次间延迟秒数（默认：2.0）
- `--attachments-dir/-a <路径>` - 附件文件夹路径，自动附加该文件夹所有文件
- `--log-file/-l <路径>` - 自定义日志文件路径（可选）
- `--resume/-r` - 强制恢复未完成任务，跳过用户交互
- `--clean-logs <天数>` - 清理N天前的旧日志文件

### 使用示例汇总

**基础邮件发送：**
```bash
python utilities/mail/BulkMail.py emails.txt verification --subject "验证码"
```

**带附件发送：**
```bash
python utilities/mail/BulkMail.py emails.txt marketing \
  --subject "产品资料" \
  --attachments-dir utilities/mail/attachments
```

**自定义参数：**
```bash
python utilities/mail/BulkMail.py emails.txt welcome \
  --subject "欢迎加入" \
  --batch-size 20 \
  --delay 3.0 \
  --log-file custom_log.log
```

**强制恢复任务：**
```bash
python utilities/mail/BulkMail.py emails.txt verification \
  --subject "验证码" \
  --resume
```

**日志维护：**
```bash
# 清理7天前的旧日志
python utilities/mail/BulkMail.py --clean-logs 7
```

## 🛠️ 高级功能

### 自定义批次参数
```bash
# 小批次快速发送（验证码等紧急邮件）
python BulkMail.py emails.txt verification --subject "验证码" --batch-size 5 --delay 0.5

# 大批次慢速发送（营销邮件）  
python BulkMail.py marketing.txt marketing --subject "优惠活动" --batch-size 10 --delay 5.0
```

### 清理旧日志
```bash
# 清理7天前的旧日志文件
python BulkMail.py --clean-logs 7

# 清理30天前的旧日志文件
python BulkMail.py --clean-logs 30
```

## 🔧 故障排除

### 常见问题

**1. 模块导入失败**
```
❌ 模块导入失败: No module named 'utilities.mail'
```
解决方案：确保在 `cry_backend` 目录下运行，并激活虚拟环境

**2. 邮箱文件格式错误**
```
❌ 文件中未找到有效的邮箱地址: emails.txt
```
解决方案：检查文件中是否包含有效的邮箱地址格式

**3. 模板不存在**
```
❌ 模板 'mytemplate' 不存在
```
解决方案：使用 `python template_converter.py --help` 查看可用模板

### 中断处理

**安全中断（CTRL+C）：**
- 当前批次完成后安全停止
- 自动保存发送状态到日志
- 支持下次断点续传

**强制中断（CTRL+Z 或系统终止）：**
- 根据日志文件自动检测中断位置
- 下次运行时提示恢复未完成任务

## 💡 使用建议

### 发送策略
```bash
# 验证码邮件（快速发送）
--batch-size 5 --delay 0.5

# 系统通知（平衡发送）
--batch-size 15 --delay 2.0

# 营销邮件（慢速发送）
--batch-size 10 --delay 5.0
```

### 最佳实践

1. **测试先行**：用小文件测试配置
2. **监控进度**：关注成功率和错误信息
3. **分批发送**：大量邮件分多次发送
4. **保留日志**：定期备份重要的发送日志
5. **错误分析**：分析失败原因，调整发送策略

## 📈 性能优化

### 批次大小建议
- **小文件（<50邮箱）**：batch-size 10-15
- **中文件（50-200邮箱）**：batch-size 15-25  
- **大文件（200+邮箱）**：batch-size 20-30

### 延迟时间建议
- **紧急邮件**：delay 0.5-1.0秒
- **通知邮件**：delay 2.0-3.0秒
- **营销邮件**：delay 3.0-5.0秒

## 🔐 安全注意事项

1. **邮箱隐私**：邮箱文件请妥善保管
2. **日志安全**：日志包含邮箱地址，注意文件权限
3. **发送限制**：遵守邮件服务商的发送频率限制
4. **内容合规**：确保邮件内容符合反垃圾邮件规定
