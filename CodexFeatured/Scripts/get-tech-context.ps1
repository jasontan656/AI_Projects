# get-tech-context.ps1
# 为 TechDecisionsGeneration_V2 工作流自动获取技术决策生成所需的上下文信息
# 版本: 2.1

param(
    [switch]$Json  # 是否以 JSON 格式输出
)

$ErrorActionPreference = "Stop"

# 配置路径
$DevPlansPath = "D:\AI_Projects\CodexFeatured\DevPlans"

function Find-LatestDevPlan {
    # 查找同时包含 DemandDescription.md 和 DevPlan.md 的最新目录
    $candidates = Get-ChildItem -Path $DevPlansPath -Directory | Where-Object {
        $demandFile = Join-Path $_.FullName "DemandDescription.md"
        $planFile = Join-Path $_.FullName "DevPlan.md"
        
        (Test-Path $demandFile) -and (Test-Path $planFile)
    } | Sort-Object Name -Descending
    
    if ($candidates.Count -eq 0) {
        Write-Error "未找到同时包含需求文档（DemandDescription.md）和开发计划（DevPlan.md）的目录"
        exit 1
    }
    
    # 返回最新的（编号最大的）
    return $candidates[0]
}

function Parse-DirName {
    param([string]$DirName)
    
    # 格式: 005_TelegramChatKnowledgeCuration
    if ($DirName -match '^(\d{3})_(.+)$') {
        return @{
            Count3D = $Matches[1]
            IntentTitle = $Matches[2]
        }
    }
    
    Write-Error "目录名格式不符合规范: $DirName (期望格式: ###_IntentTitle)"
    exit 1
}

# 主逻辑
try {
    $targetDir = Find-LatestDevPlan
    $parsed = Parse-DirName -DirName $targetDir.Name
    
    $demandPath = Join-Path $targetDir.FullName "DemandDescription.md"
    $planPath = Join-Path $targetDir.FullName "DevPlan.md"
    $techPath = Join-Path $targetDir.FullName "Tech_Decisions.md"
    
    $result = @{
        TARGET_DIR = $targetDir.FullName
        COUNT_3D = $parsed.Count3D
        INTENT_TITLE_2_4 = $parsed.IntentTitle
        DEMAND_PATH = $demandPath
        PLAN_PATH = $planPath
        TECH_PATH = $techPath
        EXISTING_TECH = (Test-Path $techPath)
    }
    
    if ($Json) {
        $result | ConvertTo-Json -Compress
    } else {
        Write-Host "找到最新开发计划:" -ForegroundColor Green
        Write-Host "  目录: $($result.TARGET_DIR)"
        Write-Host "  编号: $($result.COUNT_3D)"
        Write-Host "  标识: $($result.INTENT_TITLE_2_4)"
        Write-Host "  需求文档: $(if (Test-Path $demandPath) { '存在' } else { '不存在' })"
        Write-Host "  开发计划: $(if (Test-Path $planPath) { '存在' } else { '不存在' })"
        Write-Host "  技术决策: $(if (Test-Path $techPath) { '已存在(将覆盖)' } else { '待生成' })"
    }
    
    exit 0
}
catch {
    Write-Error "执行失败: $_"
    exit 1
}

