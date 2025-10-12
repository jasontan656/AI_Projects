# get-test-context.ps1
# 为测试工作流自动获取上下文
# 版本: 2.0

param(
    [switch]$Json  # 是否以 JSON 格式输出
)

$ErrorActionPreference = "Stop"

# 配置路径
$DevPlansPath = "D:\AI_Projects\CodexFeatured\DevPlans"
$SimulationTestPath = "D:\AI_Projects\Kobe\SimulationTest"

function Find-LatestDevProject {
    # 查找包含 DemandDescription.md 的最新项目
    $candidates = Get-ChildItem -Path $DevPlansPath -Directory | Where-Object {
        $demandFile = Join-Path $_.FullName "DemandDescription.md"
        Test-Path $demandFile
    } | Sort-Object Name -Descending
    
    if ($candidates.Count -eq 0) {
        Write-Error "未找到包含需求文档的开发项目"
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
    $targetDir = Find-LatestDevProject
    $parsed = Parse-DirName -DirName $targetDir.Name
    
    # 提取模块名称（通常与IntentTitle相关，但需要简化）
    $moduleName = $parsed.IntentTitle
    
    $demandPath = Join-Path $targetDir.FullName "DemandDescription.md"
    $planPath = Join-Path $targetDir.FullName "DevPlan.md"
    $techPath = Join-Path $targetDir.FullName "Tech_Decisions.md"
    $tasksPath = Join-Path $targetDir.FullName "Tasks.md"
    
    $testScenarioFile = Join-Path $SimulationTestPath "$($moduleName)_testscenarios.md"
    
    $result = @{
        TARGET_DIR = $targetDir.FullName
        COUNT_3D = $parsed.Count3D
        INTENT_TITLE_2_4 = $parsed.IntentTitle
        MODULE_NAME = $moduleName
        DEMAND_PATH = $demandPath
        PLAN_PATH = $planPath
        TECH_PATH = $techPath
        TASKS_PATH = $tasksPath
        TEST_SCENARIO_FILE = $testScenarioFile
        EXISTING_SCENARIO = (Test-Path $testScenarioFile)
    }
    
    if ($Json) {
        $result | ConvertTo-Json -Compress
    } else {
        Write-Host "找到最新开发项目:" -ForegroundColor Green
        Write-Host "  目录: $($result.TARGET_DIR)"
        Write-Host "  编号: $($result.COUNT_3D)"
        Write-Host "  标识: $($result.INTENT_TITLE_2_4)"
        Write-Host "  模块名: $($result.MODULE_NAME)"
        Write-Host "  需求文档: $(if (Test-Path $demandPath) { '存在' } else { '不存在' })"
        Write-Host "  开发计划: $(if (Test-Path $planPath) { '存在' } else { '不存在' })"
        Write-Host "  技术决策: $(if (Test-Path $techPath) { '存在' } else { '不存在' })"
        Write-Host "  任务清单: $(if (Test-Path $tasksPath) { '存在' } else { '不存在' })"
        Write-Host "  测试场景: $(if (Test-Path $testScenarioFile) { '已存在' } else { '待生成' })"
    }
    
    exit 0
}
catch {
    Write-Error "执行失败: $_"
    exit 1
}

