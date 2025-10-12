# get-qa-context.ps1
# 为深度学习问答工作流自动获取上下文
# 版本: 2.0

param(
    [switch]$Json  # 是否以 JSON 格式输出
)

$ErrorActionPreference = "Stop"

# 配置路径
$QAPath = "D:\AI_Projects\Learning\QA"

function Get-NextQANumber {
    # 查找现有QA文件的最大编号
    if (-not (Test-Path $QAPath)) {
        New-Item -ItemType Directory -Path $QAPath -Force | Out-Null
        return "001"
    }
    
    $existingFiles = Get-ChildItem -Path $QAPath -Filter "*.md" -File | Where-Object {
        $_.Name -match '^\d{3}_'
    }
    
    if ($existingFiles.Count -eq 0) {
        return "001"
    }
    
    # 提取所有编号
    $numbers = $existingFiles | ForEach-Object {
        if ($_.Name -match '^(\d{3})_') {
            [int]$Matches[1]
        }
    }
    
    # 获取最大编号并+1
    $maxNumber = ($numbers | Measure-Object -Maximum).Maximum
    $nextNumber = $maxNumber + 1
    
    # 格式化为3位数字
    return $nextNumber.ToString("000")
}

# 主逻辑
try {
    $nextNumber = Get-NextQANumber
    
    $result = @{
        OUTPUT_DIR = $QAPath
        COUNT_3D = $nextNumber
        EXISTING_FILES_COUNT = (Get-ChildItem -Path $QAPath -Filter "*.md" -File -ErrorAction SilentlyContinue).Count
    }
    
    if ($Json) {
        $result | ConvertTo-Json -Compress
    } else {
        Write-Host "深度学习问答上下文:" -ForegroundColor Green
        Write-Host "  输出目录: $($result.OUTPUT_DIR)"
        Write-Host "  下一个编号: $($result.COUNT_3D)"
        Write-Host "  现有文件数: $($result.EXISTING_FILES_COUNT)"
    }
    
    exit 0
}
catch {
    Write-Error "执行失败: $_"
    exit 1
}

