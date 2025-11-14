param(
    [string]$WorkflowId = "wf-demo",
    [string]$Channel = "telegram",
    [string]$Env = "local",
    [string]$BaseUrl,
    [string]$ActorId = "ops-cli",
    [string]$ActorRoles = "admin",
    [string]$SlackWebhook = "",
    [string]$PagerDutyRoutingKey = "",
    [string]$PagerDutyEventsUrl = "https://events.pagerduty.com/v2/enqueue",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..\..\..")
$summaryPath = Join-Path $scriptRoot "Step-11_ops_matrix_summary.json"
$defaultBaseUrls = @{
    "local"   = "http://localhost:8000"
    "staging" = "http://localhost:8000"
}

if (-not $BaseUrl) {
    $key = $Env.ToLower()
    if ($defaultBaseUrls.ContainsKey($key)) {
        $BaseUrl = $defaultBaseUrls[$key]
    }
    else {
        $BaseUrl = $defaultBaseUrls["local"]
    }
}

$env:PYTHONPATH = "src"

$results = @()
$overallSuccess = $true

function Invoke-OpsStep {
    param(
        [string]$Name,
        [scriptblock]$ScriptBlock
    )
    $global:results
    $global:overallSuccess
    $start = Get-Date
    $status = "ok"
    $errorMessage = $null
    try {
        & $ScriptBlock
        if ($LASTEXITCODE -ne 0) {
            throw "Process exited with $LASTEXITCODE"
        }
    }
    catch {
        $status = "failed"
        $errorMessage = $_.Exception.Message
        $global:overallSuccess = $false
        Write-Warning "[$Name] failed: $errorMessage"
    }
    $duration = [Math]::Round(((Get-Date) - $start).TotalSeconds, 2)
    $entry = [ordered]@{
        name = $Name
        status = $status
        durationSeconds = $duration
    }
    if ($errorMessage) {
        $entry.error = $errorMessage
    }
    $global:results += $entry
}

Push-Location $repoRoot
try {
    Write-Host "[ops-matrix] Using base URL $BaseUrl for env $Env"
    Invoke-OpsStep -Name "binding-refresh" -ScriptBlock {
        $args = @(
            "scripts/refresh_binding.py",
            "--workflow", $WorkflowId,
            "--channel", $Channel,
            "--base-url", $BaseUrl,
            "--actor-id", $ActorId,
            "--actor-roles", $ActorRoles
        )
        Write-Host "[binding-refresh] python $($args -join ' ')"
        & python @args
    }

    Invoke-OpsStep -Name "telemetry-probe" -ScriptBlock {
        $probeScript = "AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-06_telemetry_probe.py"
        $seedScript = "AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-06_seed_coverage.py"
        $seedArgs = @(
            $seedScript,
            "--workflow", $WorkflowId,
            "--status", "passed",
            "--actor-id", $ActorId
        )
        Write-Host "[telemetry-probe] python $($seedArgs -join ' ')"
        & python @seedArgs
        $triggerBody = @{
            scenarios = @("ops-matrix")
            mode      = "webhook"
        } | ConvertTo-Json
        try {
            Invoke-RestMethod `
                -Uri "$BaseUrl/api/workflows/$WorkflowId/tests/run" `
                -Method Post `
                -Headers @{ "X-Actor-Id" = $ActorId; "X-Actor-Roles" = $ActorRoles } `
                -ContentType "application/json" `
                -Body $triggerBody | Out-Null
            Write-Host "[telemetry-probe] triggered workflow tests/run"
        }
        catch {
            Write-Warning "[telemetry-probe] trigger failed: $($_.Exception.Message)"
        }
        $args = @(
            $probeScript,
            "--workflow", $WorkflowId,
            "--base-url", $BaseUrl,
            "--limit", "1",
            "--jsonl-count", "3",
            "--actor-id", $ActorId,
            "--actor-roles", $ActorRoles,
            "--skip-stream"
        )
        Write-Host "[telemetry-probe] python $($args -join ' ')"
        & python @args
    }

    Invoke-OpsStep -Name "workspace-nav" -ScriptBlock {
        $navScript = "AI_WorkSpace/Scripts/session_00002_bloat-scan/Step-08_workspace_nav.mjs"
        $args = @(
            $navScript,
            "--tabs=nodes,prompts,workflow"
        )
        Write-Host "[workspace-nav] node $($args -join ' ')"
        & node @args
    }
}
finally {
    Pop-Location
}

$overallStatus = if ($overallSuccess) { "ok" } else { "failed" }
$report = [ordered]@{
    env = $Env
    workflow = $WorkflowId
    channel = $Channel
    baseUrl = $BaseUrl
    actorId = $ActorId
    completedAt = (Get-Date).ToString("s")
    overallStatus = $overallStatus
    steps = $results
}

$report | ConvertTo-Json -Depth 5 | Set-Content -Path $summaryPath -Encoding UTF8
Write-Host "[ops-matrix] Summary written to $summaryPath"

if ($SlackWebhook) {
    $statuses = ($results | ForEach-Object { "* `$($_.name)` → `$($_.status)` (`$($_.durationSeconds)s`)" }) -join "\n"
    $slackPayload = @{
        text = "*Rise Ops Matrix* env=$Env overall=$overallStatus"
        blocks = @(
            @{
                type = "section"
                text = @{
                    type = "mrkdwn"
                    text = "*Rise Ops Matrix* (`$Env`) → *$overallStatus*\n$statuses"
                }
            }
        )
    } | ConvertTo-Json -Depth 5

    if ($DryRun) {
        Write-Host "[notify] Slack webhook skipped (dry-run). Payload:"
        Write-Host $slackPayload
    }
    else {
        try {
            Invoke-RestMethod -Uri $SlackWebhook -Method Post -Body $slackPayload -ContentType "application/json"
            Write-Host "[notify] Slack webhook accepted."
        }
        catch {
            Write-Warning "[notify] Slack webhook failed: $($_.Exception.Message)"
            $overallSuccess = $false
            $overallStatus = "failed"
        }
    }
}

if ($PagerDutyRoutingKey) {
    $pdPayload = @{
        routing_key  = $PagerDutyRoutingKey
        event_action = "trigger"
        payload      = @{
            summary  = "Rise ops matrix ($Env) => $overallStatus"
            source   = "rise-ops-matrix"
            severity = if ($overallSuccess) { "info" } else { "error" }
            component = "rise-backend"
            group    = $Env
            class    = "runbook"
            custom_details = @{
                workflow = $WorkflowId
                channel  = $Channel
                steps    = $results
            }
        }
    } | ConvertTo-Json -Depth 6

    if ($DryRun) {
        Write-Host "[notify] PagerDuty enqueue skipped (dry-run). Payload:"
        Write-Host $pdPayload
    }
    else {
        try {
            Invoke-RestMethod -Uri $PagerDutyEventsUrl -Method Post -Body $pdPayload -ContentType "application/json"
            Write-Host "[notify] PagerDuty event submitted."
        }
        catch {
            Write-Warning "[notify] PagerDuty event failed: $($_.Exception.Message)"
            $overallSuccess = $false
            $overallStatus = "failed"
        }
    }
}

if ($overallSuccess) {
    Write-Host "[ops-matrix] Completed successfully."
    exit 0
}
else {
    Write-Warning "[ops-matrix] Completed with failures."
    exit 1
}
