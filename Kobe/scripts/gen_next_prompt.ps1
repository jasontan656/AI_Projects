param(
  [string]$KbRoot = "D:\AI_Projects\.TelegramChatHistory\KB",
  [string]$OrganizedRoot = "D:\AI_Projects\.TelegramChatHistory\Organized",
  [string]$SpecPath = "D:\AI_Projects\.Temp\telegramextraction.md",
  [int]$MaxLines = 800
)

$ErrorActionPreference = 'Stop'

function Run-KbTool {
  param([string]$Command, [hashtable]$Params)
  $python = "D:\AI_Projects\Kobe\venv\Scripts\python.exe"
  $tool = "D:\AI_Projects\Kobe\scripts\kb_tools.py"
  $paramsJson = ($Params | ConvertTo-Json -Compress -Depth 10)
  $args = @($tool, $Command, "--kb-root", $KbRoot, "--organized-root", $OrganizedRoot, "--params", $paramsJson)
  $out = & $python $args
  return ($out | ConvertFrom-Json)
}

# Ensure KB initialized
Run-KbTool init_kb @{}

$state = Run-KbTool state_get @{}
$next = Run-KbTool queue_get_next_file @{}
$chatFile = $next.path
if (-not $chatFile) {
  Write-Output "[DONE] No remaining files."
  exit 0
}

$offset = 0
if ($state.lastProcessedFile -and $state.lastProcessedFile -eq $chatFile) {
  $offset = [int]$state.lastOffsetLine
}

$spec = Get-Content -Raw -LiteralPath $SpecPath
$indexPath = Join-Path $KbRoot 'index.json'
$indexJson = if (Test-Path -LiteralPath $indexPath) { Get-Content -Raw -LiteralPath $indexPath } else { '{"services":[]}' }

$prompt = @"
SYSTEM:
$spec

INPUT:
- chat_file=$chatFile
- start_line=$($offset + 1)
- max_lines=$MaxLines
- index_json:
$indexJson

TOOLS:
- state_get, state_update, chat_read_lines, kb_load_index, kb_upsert_service, kb_append_markdown, kb_upsert_pricing, kb_save_index, log_append

EXPECTATION:
- 严格按系统规范执行，仅通过工具调用实现读写，末尾只返回一行中文总结。
"@

Write-Output $prompt

