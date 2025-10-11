<#
.SYNOPSIS
为 DevPiplineExcute 工作流获取执行上下文信息

.DESCRIPTION
扫描现有任务清单，定位最新的 Tasks.md，输出 JSON 格式的上下文信息

.PARAMETER Json
输出 JSON 格式（用于工作流脚本集成）

.PARAMETER TargetDir
指定目标任务清单目录（可选）

.EXAMPLE
.\verify-execution.ps1 -Json
.\verify-execution.ps1 -TargetDir "001_UserRegistration"
#>

param(
    [switch]$Json,
    [string]$TargetDir
)

$ErrorActionPreference = "Stop"

# 定义路径
$REPO_ROOT = "D:/AI_Projects"
$OUTPUT_DIR_PATH = "$REPO_ROOT/CodexFeatured/DevPlans"
$TASKS_FILENAME = "Tasks.md"
$REPORT_FILENAME = "DevExcute_Run_Report.md"

# 初始化结果对象
$result = @{
    TARGET_TASKS_PATH = $null
    TARGET_DIR = $null
    EXISTING_REPORT = $false
    COUNT_3D = $null
    INTENT_TITLE_2_4 = $null
    STAGE_COUNT = 0
    ERROR = $null
}

try {
    # 检查输出目录是否存在
    if (-not (Test-Path $OUTPUT_DIR_PATH)) {
        throw "输出目录不存在: $OUTPUT_DIR_PATH"
    }

    # 查找任务清单
    if ($TargetDir) {
        # 使用指定目录
        $targetPath = Join-Path $OUTPUT_DIR_PATH $TargetDir
        if (-not (Test-Path $targetPath)) {
            throw "指定目录不存在: $targetPath"
        }
        $tasksFile = Get-Item (Join-Path $targetPath $TASKS_FILENAME) -ErrorAction SilentlyContinue
        if (-not $tasksFile) {
            throw "指定目录中未找到任务清单: $TASKS_FILENAME"
        }
    }
    else {
        # 自动扫描最新的任务清单
        $tasksFiles = Get-ChildItem -Path $OUTPUT_DIR_PATH -Recurse -Filter $TASKS_FILENAME | 
            Sort-Object LastWriteTime -Descending

        if (-not $tasksFiles) {
            throw "未找到任何任务清单 ($TASKS_FILENAME)"
        }

        $tasksFile = $tasksFiles[0]

        if (-not $Json) {
            if ($tasksFiles.Count -gt 1) {
                Write-Host "找到 $($tasksFiles.Count) 个任务清单，选择最新的" -ForegroundColor Yellow
            }
            Write-Host "目标任务清单: $($tasksFile.FullName)" -ForegroundColor Cyan
        }
    }

    # 设置目标路径
    $result.TARGET_TASKS_PATH = $tasksFile.FullName
    $result.TARGET_DIR = $tasksFile.Directory.FullName

    # 检查执行报告是否已存在
    $reportPath = Join-Path $result.TARGET_DIR $REPORT_FILENAME
    $result.EXISTING_REPORT = Test-Path $reportPath

    # 读取任务清单并提取标识信息
    $content = Get-Content $tasksFile.FullName -Raw -Encoding UTF8

    # 提取 COUNT_3D
    if ($content -match 'COUNT_3D=(\d{3})') {
        $result.COUNT_3D = $matches[1]
    }

    # 提取 INTENT_TITLE_2_4
    if ($content -match 'INTENT_TITLE_2_4=([A-Z][a-z]+(?:[A-Z][a-z]+){0,3})') {
        $result.INTENT_TITLE_2_4 = $matches[1]
    }

    # 统计阶段数量
    $stageMatches = [regex]::Matches($content, '###\s+阶段\d+')
    $result.STAGE_COUNT = $stageMatches.Count

    if (-not $Json) {
        Write-Host "`n任务清单信息:" -ForegroundColor Green
        Write-Host "  编号: $($result.COUNT_3D)"
        Write-Host "  意图标识: $($result.INTENT_TITLE_2_4)"
        Write-Host "  阶段数量: $($result.STAGE_COUNT)"
        Write-Host "  目录: $($result.TARGET_DIR)"
        if ($result.EXISTING_REPORT) {
            Write-Host "  执行报告: 已存在 (将覆盖)" -ForegroundColor Yellow
        } else {
            Write-Host "  执行报告: 未创建" -ForegroundColor Cyan
        }
    }

}
catch {
    $result.ERROR = $_.Exception.Message
    if (-not $Json) {
        Write-Host "错误: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 输出结果
if ($Json) {
    $result | ConvertTo-Json -Depth 10
}
else {
    if ($result.ERROR) {
        exit 1
    }
}

