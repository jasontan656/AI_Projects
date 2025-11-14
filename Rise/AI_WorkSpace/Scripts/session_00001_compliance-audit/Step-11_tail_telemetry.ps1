param(
    [string]$WorkflowId = "",
    [int]$Tail = 20
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\.."))
$logRoot = Join-Path $repoRoot "var\logs\test_runs"

if (-not (Test-Path $logRoot)) {
    Write-Warning "日志目录 $logRoot 不存在。"
    exit 1
}

function Get-LatestLogFile {
    param(
        [string]$TargetWorkflow
    )

    if ($TargetWorkflow) {
        $directory = Join-Path $logRoot $TargetWorkflow
        if (-not (Test-Path $directory)) {
            Write-Warning "未找到 workflow $TargetWorkflow 的日志。"
            return $null
        }
        return Get-ChildItem -Path $directory -Filter "*.jsonl" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }

    return Get-ChildItem -Path $logRoot -Recurse -Filter "*.jsonl" -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

$latest = Get-LatestLogFile -TargetWorkflow $WorkflowId

if (-not $latest) {
    Write-Warning "没有可供查看的覆盖测试日志。"
    exit 0
}

Write-Host "尾随日志文件：$($latest.FullName)" -ForegroundColor Cyan
Get-Content -Path $latest.FullName -Tail $Tail -Wait
