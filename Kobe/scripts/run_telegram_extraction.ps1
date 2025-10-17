param(
  [string]$KB_ROOT = "D:\\AI_Projects\\.TelegramChatHistory\\KB",
  [string]$ORGANIZED_ROOT = "D:\\AI_Projects\\.TelegramChatHistory\\Organized",
  [string]$SPEC_PATH = "D:\\AI_Projects\\.Temp\\telegramextraction.md",
  [string]$PS_SCRIPT = "D:\\AI_Projects\\Kobe\\scripts\\gen_next_prompt.ps1",
  [string]$PYTHON_EXE = "D:\\AI_Projects\\Kobe\\venv\\Scripts\\python.exe",
  [int]$MaxTurns = 0, # 0 = unlimited until [DONE]
  [string]$Model = ""
)

$ErrorActionPreference = 'Stop'

function Write-Info { param([string]$msg) Write-Host "[info] $msg" -ForegroundColor Cyan }
function Write-Warn { param([string]$msg) Write-Host "[warn] $msg" -ForegroundColor Yellow }
function Write-Err  { param([string]$msg) Write-Host "[err ] $msg" -ForegroundColor Red }

function Assert-File {
  param([Parameter(Mandatory)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing file: $Path" }
}

function Assert-Dir {
  param([Parameter(Mandatory)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Container)) { throw "Missing directory: $Path" }
}

# Load .env variables if present (search upward from CWD)
function Find-DotEnv {
  param([string]$StartDir)
  $dir = if ($StartDir) { $StartDir } else { (Get-Location).Path }
  while ($true) {
    $candidate = Join-Path $dir '.env'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    $parent = Split-Path $dir -Parent
    if (-not $parent -or $parent -eq $dir) { break }
    $dir = $parent
  }
  return $null
}

function Import-DotEnv {
  param([string]$Path)
  if (-not $Path) { return }
  Get-Content -LiteralPath $Path | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith('#')) { return }
    $idx = $line.IndexOf('=')
    if ($idx -lt 1) { return }
    $k = $line.Substring(0,$idx).Trim()
    $v = $line.Substring($idx+1).Trim()
    if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Trim('"') }
    if ($v.StartsWith("'") -and $v.EndsWith("'")) { $v = $v.Trim("'") }
    if ($k) { Set-Item -Path Env:$k -Value $v }
  }
}

function Invoke-KbTool {
  param(
    [Parameter(Mandatory)][string]$Command,
    [object]$Params
  )
  $tool = "D:\\AI_Projects\\Kobe\\scripts\\kb_tools.py"
  Assert-File -Path $PYTHON_EXE
  Assert-File -Path $tool
  $paramsJson = if ($Params) { ($Params | ConvertTo-Json -Compress -Depth 20) } else { '{}' }
  $args = @(
    $tool, $Command,
    '--kb-root', $KB_ROOT,
    '--organized-root', $ORGANIZED_ROOT,
    '--params', $paramsJson
  )
  $out = & $PYTHON_EXE $args 2>$null
  try { return ($out | ConvertFrom-Json) } catch { throw "kb_tool output not JSON for ${Command}: $out" }
}

function Get-Next-Prompt {
  param([int]$MaxLines = 800)
  Assert-File -Path $PS_SCRIPT
  $args = @(
    '-NoProfile','-File', $PS_SCRIPT,
    '-KbRoot', $KB_ROOT,
    '-OrganizedRoot', $ORGANIZED_ROOT,
    '-SpecPath', $SPEC_PATH,
    '-MaxLines', $MaxLines
  )
  $out = & pwsh @args
  return ($out -join "`n").Trim()
}

# Basic OpenAI function-calling client over REST
function Invoke-OpenAIChatWithTools {
  param(
    [Parameter(Mandatory)][string]$ModelName,
    [Parameter(Mandatory)][string]$SystemPrompt,
    [Parameter(Mandatory)][string]$UserPrompt
  )

  $apiKey = $env:OPENAI_API_KEY
  if (-not $apiKey) { throw "OPENAI_API_KEY not set. Please set environment variable." }
  if (-not $ModelName) { $ModelName = 'gpt-4o-mini' }

  $uri = 'https://api.openai.com/v1/chat/completions'

  $functions = @(
    @{ name='state_get'; parameters=@{ type='object'; properties=@{}; required=@() } },
    @{ name='state_update'; parameters=@{ type='object'; properties=@{ lastProcessedFile=@{type='string'}; lastOffsetLine=@{type='integer'}; filesDoneAppend=@{type='string'} }; required=@() } },
    @{ name='chat_read_lines'; parameters=@{ type='object'; properties=@{ path=@{type='string'}; start_line=@{type='integer'}; max_lines=@{type='integer'} }; required=@('path') } },
    @{ name='kb_load_index'; parameters=@{ type='object'; properties=@{}; required=@() } },
    @{ name='kb_upsert_service'; parameters=@{ type='object'; properties=@{ slug=@{type='string'}; name=@{type='string'}; aliases=@{type='array'; items=@{type='string'}}; categories=@{type='array'; items=@{type='string'}} }; required=@('name') } },
    @{ name='kb_append_markdown'; parameters=@{ type='object'; properties=@{ slug=@{type='string'}; section=@{type='string'}; markdown=@{type='string'} }; required=@('slug','markdown') } },
    @{ name='kb_upsert_pricing'; parameters=@{ type='object'; properties=@{ slug=@{type='string'}; entry=@{ type='object'; properties=@{ currency=@{type='string'}; amount=@{type='string'}; effective_date=@{type='string'}; conditions=@{type='string'}; notes=@{type='string'}; evidence=@{ type='object'; properties=@{ file=@{type='string'}; message_ids=@{type='array'; items=@{type='string'}}; dates=@{type='array'; items=@{type='string'}} } } } } }; required=@('slug','entry') } },
    @{ name='kb_save_index'; parameters=@{ type='object'; properties=@{ services=@{type='array'; items=@{type='object'} } }; required=@('services') } },
    @{ name='log_append'; parameters=@{ type='object'; properties=@{ jsonl=@{type='string'} }; required=@('jsonl') } }
  )

  $tools = @()
  foreach ($fn in $functions) {
    $tools += @{ type='function'; function=@{ name=$fn.name; parameters=$fn.parameters } }
  }

  $messages = @(
    @{ role='system'; content=$SystemPrompt },
    @{ role='user'; content=$UserPrompt }
  )

  while ($true) {
    $body = @{ 
      model = $ModelName;
      tools = $tools;
      messages = $messages
    } | ConvertTo-Json -Depth 100

    $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers @{ 'Authorization' = "Bearer $apiKey" } -ContentType 'application/json' -Body $body
    if (-not $resp.choices) { throw "OpenAI response missing choices" }
    $choice = $resp.choices[0]
    $msg = $choice.message

    if ($msg.tool_calls -or $msg.function_call) {
      # New (tools) / legacy (functions) compatibility
      if ($msg.tool_calls) {
        # Record assistant message with tool_calls (content must be string, not null)
        $assistantContent = if ($msg.content) { $msg.content } else { '' }
        $messages += @{ role='assistant'; content=$assistantContent; tool_calls=$msg.tool_calls }
        foreach ($call in $msg.tool_calls) {
          $fn = $call.function
          $name = $fn.name
          $argsText = if ($fn.arguments) { $fn.arguments } else { '{}' }
          try { $args = $argsText | ConvertFrom-Json } catch { $args = @{} }

          switch ($name) {
            'state_get'        { $toolRes = Invoke-KbTool -Command 'state_get' }
            'state_update'     { $toolRes = Invoke-KbTool -Command 'state_update' -Params $args }
            'chat_read_lines'  { $toolRes = Invoke-KbTool -Command 'chat_read_lines' -Params $args }
            'kb_load_index'    { $toolRes = Invoke-KbTool -Command 'kb_load_index' }
            'kb_upsert_service'{ $toolRes = Invoke-KbTool -Command 'kb_upsert_service' -Params $args }
            'kb_append_markdown'{ $toolRes = Invoke-KbTool -Command 'kb_append_markdown' -Params $args }
            'kb_upsert_pricing'{ $toolRes = Invoke-KbTool -Command 'kb_upsert_pricing' -Params $args }
            'kb_save_index'    { $toolRes = Invoke-KbTool -Command 'kb_save_index' -Params $args }
            'log_append'       { $toolRes = Invoke-KbTool -Command 'log_append' -Params $args }
            Default            { $toolRes = @{ ok=$false; error="unknown tool $name" } }
          }

          $toolJson = try { ($toolRes | ConvertTo-Json -Depth 50 -Compress) } catch { $null }
          if (-not $toolJson) { $toolJson = 'null' }
          $messages += @{ role='tool'; tool_call_id=$call.id; name=$name; content=$toolJson }
        }
        continue
      }
      elseif ($msg.function_call) {
        # Legacy function_call flow
        $assistantContent = if ($msg.content) { $msg.content } else { '' }
        $messages += @{ role='assistant'; content=$assistantContent; function_call=$msg.function_call }
        $fn = $msg.function_call
        $name = $fn.name
        $argsText = if ($fn.arguments) { $fn.arguments } else { '{}' }
        try { $args = $argsText | ConvertFrom-Json } catch { $args = @{} }
        switch ($name) {
          'state_get'        { $toolRes = Invoke-KbTool -Command 'state_get' }
          'state_update'     { $toolRes = Invoke-KbTool -Command 'state_update' -Params $args }
          'chat_read_lines'  { $toolRes = Invoke-KbTool -Command 'chat_read_lines' -Params $args }
          'kb_load_index'    { $toolRes = Invoke-KbTool -Command 'kb_load_index' }
          'kb_upsert_service'{ $toolRes = Invoke-KbTool -Command 'kb_upsert_service' -Params $args }
          'kb_append_markdown'{ $toolRes = Invoke-KbTool -Command 'kb_append_markdown' -Params $args }
          'kb_upsert_pricing'{ $toolRes = Invoke-KbTool -Command 'kb_upsert_pricing' -Params $args }
          'kb_save_index'    { $toolRes = Invoke-KbTool -Command 'kb_save_index' -Params $args }
          'log_append'       { $toolRes = Invoke-KbTool -Command 'log_append' -Params $args }
          Default            { $toolRes = @{ ok=$false; error="unknown tool $name" } }
        }
        $toolJson = try { ($toolRes | ConvertTo-Json -Depth 50 -Compress) } catch { $null }
        if (-not $toolJson) { $toolJson = 'null' }
        $messages += @{ role='function'; name=$name; content=$toolJson }
        continue
      }
    }

    # No tool calls: return final assistant content
    return ($msg.content -join "")
  }
}

function Invoke-AITurn {
  param([string]$NextPrompt)
  # If no OPENAI_API_KEY, run a minimal deterministic fallback to advance offsets only.
  if (-not $env:OPENAI_API_KEY) {
    # Parse essentials from the prompt (restrict to INPUT:...TOOLS: block)
    $inputIdx = $NextPrompt.IndexOf('INPUT:')
    $toolsIdx = $NextPrompt.IndexOf('TOOLS:')
    $scope = if ($inputIdx -ge 0 -and $toolsIdx -gt $inputIdx) { $NextPrompt.Substring($inputIdx, $toolsIdx - $inputIdx) } else { $NextPrompt }
    $rxOpts = [System.Text.RegularExpressions.RegexOptions]::Multiline
    $mPaths = [regex]::Matches($scope, "^\s*-\s*chat_file=(?<p>.+)$", $rxOpts)
    $mStarts = [regex]::Matches($scope, "^\s*-\s*start_line=(?<n>\d+)$", $rxOpts)
    $mMaxes = [regex]::Matches($scope, "^\s*-\s*max_lines=(?<n>\d+)$", $rxOpts)
    $chatFile = if ($mPaths.Count -gt 0) { $mPaths[$mPaths.Count-1].Groups['p'].Value.Trim() } else { '' }
    $start = if ($mStarts.Count -gt 0) { [int]$mStarts[$mStarts.Count-1].Groups['n'].Value } else { 1 }
    $max = if ($mMaxes.Count -gt 0) { [int]$mMaxes[$mMaxes.Count-1].Groups['n'].Value } else { 800 }

    # Ensure state points at current file
    $st = Invoke-KbTool -Command 'state_get'
    if ($st.lastProcessedFile -ne $chatFile) {
      $null = Invoke-KbTool -Command 'state_update' -Params @{ lastProcessedFile = $chatFile }
    }

    # Read chunk
    $res = Invoke-KbTool -Command 'chat_read_lines' -Params @{ path=$chatFile; start_line=$start; max_lines=$max }
    $next = [int]$res.next_line

    # Update offset
    $null = Invoke-KbTool -Command 'state_update' -Params @{ lastProcessedFile = $chatFile; lastOffsetLine = $next }

    $updated = 0
    $newPrices = 0

    if ($res.eof -eq $true) {
      # Mark file done and reset
      $null = Invoke-KbTool -Command 'state_update' -Params @{ filesDoneAppend = $chatFile; lastProcessedFile = $null; lastOffsetLine = 0 }
    }

    # Append minimal log
    $payload = @{ file=$chatFile; processed_lines=($res.lines.Count); updated_services=@(); new_prices=$newPrices; next_offset=$next } | ConvertTo-Json -Compress
    $null = Invoke-KbTool -Command 'log_append' -Params @{ jsonl=$payload }

    $base = [System.IO.Path]::GetFileName($chatFile)
    return "已处理 $base，更新服务 $updated 个，新增价格 $newPrices 个，偏移行 $next"
  }
  # Otherwise, use OpenAI function-calling agent
  $system = $NextPrompt
  $user   = "请严格按 SYSTEM/INPUT/TOOLS/EXPECTATION 执行，仅用工具读写，最后返回一行中文总结。"
  $modelName = if ($Model) { $Model } else { 'gpt-4o-mini' }
  return (Invoke-OpenAIChatWithTools -ModelName $modelName -SystemPrompt $system -UserPrompt $user)
}

# 1) Import .env, then validate paths
$dotenv = Find-DotEnv -StartDir (Get-Location).Path
if (-not $dotenv) {
  $cand1 = Join-Path $PSScriptRoot '..\.env'
  if (Test-Path -LiteralPath $cand1 -PathType Leaf) { $dotenv = (Resolve-Path -LiteralPath $cand1).Path }
}
if (-not $dotenv) {
  $cand2 = Join-Path $PSScriptRoot '..\..\.env'
  if (Test-Path -LiteralPath $cand2 -PathType Leaf) { $dotenv = (Resolve-Path -LiteralPath $cand2).Path }
}
if ($dotenv) { Write-Info "Loading .env from $dotenv"; Import-DotEnv -Path $dotenv }
if (-not $Model -and $env:OPENAI_MODEL) { $Model = $env:OPENAI_MODEL }

# 2) Validate paths
Assert-Dir -Path $ORGANIZED_ROOT
Assert-File -Path $SPEC_PATH
Assert-File -Path $PS_SCRIPT
Assert-File -Path $PYTHON_EXE

# 3) Ensure KB initialized (idempotent)
Write-Info "Ensuring KB initialized..."
$null = Invoke-KbTool -Command 'init_kb'

# 4) Loop
$turn = 0
while ($true) {
  if ($MaxTurns -gt 0 -and $turn -ge $MaxTurns) { Write-Info "Reached MaxTurns=$MaxTurns"; break }
  $turn += 1
  Write-Info "Turn #${turn}: generating next prompt..."
  $prompt = Get-Next-Prompt -MaxLines 800
  if ($prompt -match '^\[DONE\]') { Write-Info "No remaining files. Done."; break }

  Write-Info "Turn #${turn}: invoking AI turn..."
  $summary = Invoke-AITurn -NextPrompt $prompt
  if (-not $summary) { $summary = "（本轮无输出）" }
  $summaryLine = ($summary -split "`n")[0].Trim()
  Write-Host $summaryLine
}

Write-Info "All done."





