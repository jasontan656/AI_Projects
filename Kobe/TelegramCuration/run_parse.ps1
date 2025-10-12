param(
  [Parameter(Mandatory=$true)][string]$ChatId,
  [string]$Path = 'D:\AI_Projects\TelegramChatHistory\Original',
  [string]$Since,
  [string]$Until,
  [string]$SaveJson,
  [int]$Limit = 3,
  [switch]$Quiet
)

$ErrorActionPreference='Stop'

$py = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

$argsList = @('-m','Kobe.TelegramCuration','--chat-id', $ChatId, '--limit', $Limit)
if ($Path) { $argsList += @('--path', $Path) }
if ($Since) { $argsList += @('--since', $Since) }
if ($Until) { $argsList += @('--until', $Until) }
if ($SaveJson) { $argsList += @('--save-json', $SaveJson) }
if ($Quiet) { $argsList += @('--quiet') }

& $py @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
