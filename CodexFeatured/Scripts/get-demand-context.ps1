<#
.SYNOPSIS
为 DevFuncDemandsWrite 工作流获取上下文信息

.DESCRIPTION
扫描现有需求文档目录，计算下一个可用编号，输出 JSON 格式的上下文信息

.PARAMETER Json
输出 JSON 格式（用于工作流脚本集成）

.EXAMPLE
.\get-demand-context.ps1 -Json
#>

param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"

# 定义路径
$REPO_ROOT = "D:/AI_Projects"
$OUTPUT_DIR_PATH = "$REPO_ROOT/CodexFeatured/DevPlans"

# 初始化结果对象
$result = @{
    OUTPUT_DIR_PATH = $OUTPUT_DIR_PATH
    EXISTING_PLANS = @()
    NEXT_COUNT = "001"
    PROJECT_ROOT = $REPO_ROOT
    ERROR = $null
}

try {
    # 检查输出目录是否存在
    if (-not (Test-Path $OUTPUT_DIR_PATH)) {
        # 创建目录
        New-Item -ItemType Directory -Path $OUTPUT_DIR_PATH -Force | Out-Null
        Write-Host "创建输出目录: $OUTPUT_DIR_PATH" -ForegroundColor Green
    }

    # 扫描现有目录
    $existingDirs = Get-ChildItem -Path $OUTPUT_DIR_PATH -Directory | Where-Object {
        $_.Name -match '^\d{3}_'
    }

    if ($existingDirs) {
        # 提取编号并排序
        $numbers = $existingDirs | ForEach-Object {
            if ($_.Name -match '^(\d{3})_') {
                [int]$matches[1]
            }
        } | Sort-Object

        # 计算下一个编号
        $maxNumber = $numbers | Select-Object -Last 1
        $nextNumber = $maxNumber + 1
        $result.NEXT_COUNT = "{0:D3}" -f $nextNumber

        # 记录现有计划
        $result.EXISTING_PLANS = $existingDirs | ForEach-Object {
            @{
                Name = $_.Name
                Path = $_.FullName
                CreatedTime = $_.CreationTime.ToString("yyyy-MM-dd HH:mm:ss")
                ModifiedTime = $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
            }
        }

        if (-not $Json) {
            Write-Host "找到 $($existingDirs.Count) 个现有计划目录" -ForegroundColor Cyan
            Write-Host "最大编号: $maxNumber" -ForegroundColor Cyan
            Write-Host "下一个编号: $($result.NEXT_COUNT)" -ForegroundColor Cyan
        }
    }
    else {
        if (-not $Json) {
            Write-Host "未找到现有计划目录，使用编号: 001" -ForegroundColor Yellow
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
    Write-Host "`n上下文信息:" -ForegroundColor Green
    Write-Host "  输出目录: $($result.OUTPUT_DIR_PATH)"
    Write-Host "  下一个编号: $($result.NEXT_COUNT)"
    Write-Host "  现有计划数量: $($result.EXISTING_PLANS.Count)"
}

