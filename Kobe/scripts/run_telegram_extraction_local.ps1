param(
  [string]$KB_ROOT = "D:\\AI_Projects\\.TelegramChatHistory\\KB",
  [string]$ORGANIZED_ROOT = "D:\\AI_Projects\\.TelegramChatHistory\\Organized",
  [int]$MaxLines = 800
)

$ErrorActionPreference = 'Stop'

function Write-Info { param([string]$msg) Write-Host "[info] $msg" -ForegroundColor Cyan }
function Assert-File { param([Parameter(Mandatory)][string]$Path) if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" } }

function Invoke-KbTool {
  param(
    [Parameter(Mandatory)][string]$Command,
    [object]$Params
  )
  $tool = "D:\\AI_Projects\\Kobe\\scripts\\kb_tools.py"
  $py   = "D:\\AI_Projects\\Kobe\\venv\\Scripts\\python.exe"
  Assert-File -Path $py
  Assert-File -Path $tool
  $paramsJson = if ($Params) { ($Params | ConvertTo-Json -Compress -Depth 20) } else { '{}' }
  $args = @($tool, $Command, '--kb-root', $KB_ROOT, '--organized-root', $ORGANIZED_ROOT, '--params', $paramsJson)
  $out = & $py $args 2>$null
  try { return ($out | ConvertFrom-Json) } catch { throw "kb_tool output not JSON for ${Command}: $out" }
}

# 1) Init
$null = Invoke-KbTool -Command 'init_kb'
$state = Invoke-KbTool -Command 'state_get'
$next  = Invoke-KbTool -Command 'queue_get_next_file'
$chatFile = $next.path
if (-not $chatFile) { Write-Host "[DONE] 无剩余文件。"; exit 0 }

$offset = 0
if ($state.lastProcessedFile -and $state.lastProcessedFile -eq $chatFile) { $offset = [int]$state.lastOffsetLine }

# 2) Read chunk
$res = Invoke-KbTool -Command 'chat_read_lines' -Params @{ path=$chatFile; start_line=($offset+1); max_lines=$MaxLines }
$nextLine = [int]$res.next_line

# 3) Heuristic extraction (generic business)
$lines = @($res.lines)
$priceRegexes = @(
  '(?i)(?<cur>USD|US\$|\$)\s*(?<amt>\d{1,3}(?:[\,\.]\d{3})*(?:[\.]\d{1,2})?)',
  '(?i)(?<cur>CNY|RMB|￥|¥)\s*(?<amt>\d{1,3}(?:[\,\.]\d{3})*(?:[\.]\d{1,2})?)',
  '(?i)(?<cur>PHP|₱)\s*(?<amt>\d{1,3}(?:[\,\.]\d{3})*(?:[\.]\d{1,2})?)',
  '(?i)(?<cur>EUR|€)\s*(?<amt>\d{1,3}(?:[\,\.]\d{3})*(?:[\.]\d{1,2})?)',
  '(?i)(?<cur>HKD|SGD|GBP|AUD|CAD)\s*(?<amt>\d{1,3}(?:[\,\.]\d{3})*(?:[\.]\d{1,2})?)'
)
$bizKeywords = @('业务','服务','套餐','价格','报价','费用','费','会员','订阅','购买','下单','开票','税','合约','合同','方案','版本','代理','代办','办理','咨询','顾问','周期','每月','每年','一次性','trial','service','package','plan','pricing','price','fee','subscription','member','invoice','tax','quote','offer','contract')

# Discover chat title from first 30 lines
$chatTitle = ''
for ($i=0; $i -lt [Math]::Min(30, $lines.Count); $i++) {
  $obj = $null
  try { $obj = $lines[$i] | ConvertFrom-Json -ErrorAction Stop } catch { $obj=$null }
  if ($null -ne $obj) {
    if ($obj.chat_header.title) { $chatTitle = [string]$obj.chat_header.title; break }
    if ($obj.header.title) { $chatTitle = [string]$obj.header.title; break }
    if ($obj.peer.title) { $chatTitle = [string]$obj.peer.title; break }
    if ($obj.chat.title) { $chatTitle = [string]$obj.chat.title; break }
  }
}
if (-not $chatTitle) { $chatTitle = [System.IO.Path]::GetFileNameWithoutExtension($chatFile) }
$serviceName = "$chatTitle 业务"

$svcRes = Invoke-KbTool -Command 'kb_upsert_service' -Params @{ name = $serviceName; aliases = @($chatTitle); categories = @('business') }
$slug = $svcRes.slug
$updated = 1
$priceCount = 0

$bizSnippets = New-Object System.Collections.Generic.List[string]
for ($i=0; $i -lt $lines.Count; $i++) {
  $line = [string]$lines[$i]
  $obj = $null
  try { $obj = $line | ConvertFrom-Json -ErrorAction Stop } catch { $obj=$null }
  $text = ''
  $msgId = $null
  $ts = $null
  if ($null -ne $obj) {
    if ($obj.text) { $text = [string]$obj.text }
    elseif ($obj.message) { $text = [string]$obj.message }
    elseif ($obj.content) { $text = [string]$obj.content }
    $msgId = $obj.id
    if ($obj.date) { $ts = [string]$obj.date } elseif ($obj.timestamp) { $ts = [string]$obj.timestamp }
  } else {
    $text = $line
  }
  if (-not $text) { continue }

  $hasBiz = $false
  foreach ($kw in $bizKeywords) { if ($text -like "*${kw}*") { $hasBiz = $true; break } }
  if ($hasBiz) { $bizSnippets.Add("- " + ($text.Trim())) }

  foreach ($rx in $priceRegexes) {
    $m = [regex]::Match($text, $rx)
    if ($m.Success) {
      $cur = $m.Groups['cur'].Value
      if ($cur -eq 'US$' -or $cur -eq '$') { $cur = 'USD' }
      if ($cur -eq '￥' -or $cur -eq '¥') { $cur = 'CNY' }
      if ($cur -eq '₱') { $cur = 'PHP' }
      $amt = $m.Groups['amt'].Value
      $entry = @{ currency=$cur; amount=$amt; effective_date=($ts ? $ts : ''); conditions=$text; notes=''; evidence=@{ file=$chatFile; message_ids=@($msgId ? [string]$msgId : ''); dates=@($ts ? [string]$ts : '') } }
      $pr = Invoke-KbTool -Command 'kb_upsert_pricing' -Params @{ slug=$slug; entry=$entry }
      if ($pr.ok) { $priceCount++ }
      break
    }
  }
}

if ($bizSnippets.Count -gt 0) {
  $md = "本段自动提取（行 $($offset+1)-$([Math]::Max($offset+1, $nextLine-1))）：`n" + ($bizSnippets -join "`n") + "`n"
  $null = Invoke-KbTool -Command 'kb_append_markdown' -Params @{ slug=$slug; section='摘要'; markdown=$md }
}

# 4) Update state and log
$null = Invoke-KbTool -Command 'state_update' -Params @{ lastProcessedFile = $chatFile; lastOffsetLine = $nextLine }
if ($res.eof -eq $true) {
  $null = Invoke-KbTool -Command 'state_update' -Params @{ filesDoneAppend = $chatFile; lastProcessedFile = $null; lastOffsetLine = 0 }
}
$payload = @{ file=$chatFile; processed_lines=($res.lines.Count); updated_services=@($slug); new_prices=$priceCount; next_offset=$nextLine } | ConvertTo-Json -Compress
$null = Invoke-KbTool -Command 'log_append' -Params @{ jsonl=$payload }

# 5) One-line summary
$base = [System.IO.Path]::GetFileName($chatFile)
Write-Host "已处理 $base，更新服务 $updated 个，新增价格 $priceCount 个，偏移行 $nextLine"

