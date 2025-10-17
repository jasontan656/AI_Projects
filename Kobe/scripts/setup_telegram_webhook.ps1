# Telegram Bot Webhook 设置脚本
# 使用方法：./setup_telegram_webhook.ps1

# 配置（从 .env 读取或手动设置）
$BOT_TOKEN = "7645742612:AAEwIKz18d5KZvpkO36UXL4jE-HXlQ2B538"
$BOT_NAME = "fourwaysgroup"

# 获取 ngrok 地址（自动从 ngrok API 获取）
Write-Host "正在获取 ngrok 地址..." -ForegroundColor Yellow
try {
    $ngrokInfo = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
    $WEBHOOK_URL = $ngrokInfo.tunnels[0].public_url
    Write-Host "ngrok 地址: $WEBHOOK_URL" -ForegroundColor Green
} catch {
    Write-Host "无法自动获取 ngrok 地址，请手动输入：" -ForegroundColor Red
    $WEBHOOK_URL = Read-Host "请输入 ngrok HTTPS 地址（例如：https://abc123.ngrok-free.app）"
}

# 构建完整的 Webhook URL
$FULL_WEBHOOK_URL = "$WEBHOOK_URL/telegram/webhook/$BOT_NAME"

Write-Host "`n正在设置 Webhook..." -ForegroundColor Yellow
Write-Host "机器人: $BOT_NAME" -ForegroundColor Cyan
Write-Host "Webhook URL: $FULL_WEBHOOK_URL" -ForegroundColor Cyan

# 调用 Telegram API 设置 Webhook
$telegramApiUrl = "https://api.telegram.org/bot$BOT_TOKEN/setWebhook?url=$FULL_WEBHOOK_URL"

try {
    $response = Invoke-RestMethod -Uri $telegramApiUrl -Method Get
    
    if ($response.ok) {
        Write-Host "`n✓ Webhook 设置成功！" -ForegroundColor Green
        Write-Host "描述: $($response.description)" -ForegroundColor Green
    } else {
        Write-Host "`n✗ Webhook 设置失败！" -ForegroundColor Red
        Write-Host "错误: $($response.description)" -ForegroundColor Red
    }
} catch {
    Write-Host "`n✗ 请求失败：$_" -ForegroundColor Red
}

# 验证 Webhook 设置
Write-Host "`n正在验证 Webhook 设置..." -ForegroundColor Yellow
$getWebhookUrl = "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"

try {
    $webhookInfo = Invoke-RestMethod -Uri $getWebhookUrl -Method Get
    
    if ($webhookInfo.ok) {
        Write-Host "`n当前 Webhook 信息：" -ForegroundColor Cyan
        Write-Host "URL: $($webhookInfo.result.url)" -ForegroundColor White
        Write-Host "待处理更新数: $($webhookInfo.result.pending_update_count)" -ForegroundColor White
        Write-Host "最大连接数: $($webhookInfo.result.max_connections)" -ForegroundColor White
        
        if ($webhookInfo.result.last_error_date) {
            Write-Host "`n⚠ 最后错误: $($webhookInfo.result.last_error_message)" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "验证失败：$_" -ForegroundColor Red
}

Write-Host "`n完成！现在可以在 Telegram 中测试机器人了。" -ForegroundColor Green
Write-Host "找到 @fourwaysgroupbot 发送消息测试。" -ForegroundColor Green

