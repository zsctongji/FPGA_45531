$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskPackageDir=Join-Path $taskRoot 'build\pc_ai_packages'
$taskSummary=Join-Path $taskRoot 'logs\c4_pc_checks.json'
$record=[ordered]@{status='RUNNING';scope='Host C4 replay, actual desktop compatibility-model inference and RISC-V object compilation only';steps=@();board_inference_passed=$false;live_camera_passed=$false}
function Invoke-TaskStep([string]$Name,[scriptblock]$Action) {
    $record.steps+=@{name=$Name;status='RUNNING'}
    & $Action
    if($LASTEXITCODE -ne 0){$record.steps[-1].status='FAIL';throw "$Name failed (exit=$LASTEXITCODE)"}
    $record.steps[-1].status='PASS'
}
try {
    $oldPreference=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    try {
        & python -c "import sys;sys.path.insert(0,r'$taskPackageDir');import ai_edge_litert,numpy;import importlib.metadata as m;assert m.version('ai-edge-litert')=='2.3.0'" *> (Join-Path $taskRoot 'logs\pc_ai_dependency_check.log')
        $taskDependenciesReady=$LASTEXITCODE -eq 0
    } finally {$ErrorActionPreference=$oldPreference}
    if(-not $taskDependenciesReady) {
        Invoke-TaskStep 'install isolated pinned PC packages' {
            & python -m pip install --target $taskPackageDir --upgrade --only-binary=:all: -r (Join-Path $PSScriptRoot 'pc_ai_requirements.txt') *> (Join-Path $taskRoot 'logs\pc_ai_install.log')
        }
    }
    Invoke-TaskStep 'native C4 and synthetic sensor replay tests plus DLL build' {
        & (Join-Path $PSScriptRoot 'build_c4_host.cmd') *> (Join-Path $taskRoot 'logs\c4_host_test.log')
    }
    Invoke-TaskStep 'actual desktop reference and 24 C4 inference replays' {
        & python (Join-Path $PSScriptRoot 'run_pc_ai.py') *> (Join-Path $taskRoot 'logs\pc_ai_run.log')
    }
    Invoke-TaskStep 'reference comparison negative tests' {
        & python (Join-Path $taskRoot 'team_work\03_ai_soc\tests\test_pc_reference.py') *> (Join-Path $taskRoot 'logs\pc_ai_reference_tests.log')
    }
    Invoke-TaskStep 'existing C1 log parser regression tests' {
        & python (Join-Path $taskRoot 'team_work\03_ai_soc\tests\test_c1_parser.py') *> (Join-Path $taskRoot 'logs\c1_parser_regression.log')
    }
    Invoke-TaskStep 'RISC-V C4 adapter object compile checks' {
        & (Join-Path $PSScriptRoot 'check_c4_riscv.ps1')
    }
    Invoke-TaskStep 'existing C1 package remains consistent' {
        & python (Join-Path $PSScriptRoot 'verify_c1_package.py')
    }
    $replay=Get-Content -LiteralPath (Join-Path $taskRoot 'logs\pc_ai\c4_replay.json') -Raw | ConvertFrom-Json
    $record.padding_class_changes=@($replay.padding_class_changes)
    $record.preprocess_policy_approved=$false
    $record.status='PASS'
} catch {
    $record.status='FAIL';$record.error=$_.Exception.Message;throw
} finally {
    $record.finished=(Get-Date).ToString('o')
    $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $taskSummary -Encoding UTF8
}
Write-Host 'PASS: PC-only checks completed. Padding policy still needs A/C review; see logs/pc_ai/preprocess_policy.json.'

