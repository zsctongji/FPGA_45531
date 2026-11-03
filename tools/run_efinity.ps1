param(
    [ValidateSet('led','camera','tinyml','camera_preprocess','camera_motion')][string]$Project='led',
    [ValidateSet('interface','map','compile')][string]$Flow='compile'
)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'file_hash.ps1')
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskEfinity=Join-Path $taskRoot 'tools\efinity\2026.1'
$tool=Join-Path $taskEfinity 'bin\efx_run.bat'
if (-not (Test-Path -LiteralPath $tool)) { throw "Efinity missing: $tool" }
$projectFiles=@{
    led='projects\01_led\LED_8bit_Test.xml'
    camera='projects\02_camera\ti60f225_oob.xml'
    tinyml='projects\03_tinyml\Ti60F225_tinyml_helloworld.xml'
    camera_preprocess='projects\04_camera_preprocess\ti60f225_oob.xml'
    camera_motion='projects\05_camera_motion\ti60f225_oob.xml'
}
$projectFile=Join-Path $taskRoot $projectFiles[$Project]
if (-not (Test-Path -LiteralPath $projectFile)) { throw "Project missing: $projectFile" }
$logDir=Join-Path $taskRoot 'logs'
New-Item -ItemType Directory -Force -Path $logDir,(Join-Path $taskRoot 'config\efinity_user') | Out-Null
$logFile=Join-Path $logDir "efinity_${Project}_${Flow}.log"
$statusFile=Join-Path $logDir "efinity_${Project}_${Flow}.json"
$runStart=Get-Date
$record=[ordered]@{
    status='RUNNING'; project=$Project; flow=$Flow; file=$projectFile
    started=$runStart.ToString('o'); stage='preflight'
    scope=if($Flow -eq 'map'){'synthesis_only'}else{'tool_flow_only'}
    physical_board_programmed=$false; board_test_passed=$false
    efinity_version=(Get-Content -LiteralPath (Join-Path $taskEfinity 'scripts\sw_version.txt') -Raw).Trim()
}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusFile -Encoding UTF8
# Official setup.bat environment, restricted to this process. No persistent PATH edit.
$unixEfinity=$taskEfinity.Replace('\','/')
$vars=@{
    EFINITY_HOME=$unixEfinity
    EFXPT_HOME="$unixEfinity/pt"
    EFXPGM_HOME="$unixEfinity/pgm"
    EFXDBG_HOME="$unixEfinity/debugger"
    EFXIPM_HOME="$unixEfinity/ipm"
    EFXSVF_HOME="$unixEfinity/debugger/svf_player"
    PYTHONHOME=(Join-Path $taskEfinity 'python311')
    PYTHONUTF8='1'
    EFINITY_USER_DIR_INI=(Join-Path $taskRoot 'config\efinity_user\user_dir.ini').Replace('\','/')
    PATH="$taskEfinity\python311\bin;$taskEfinity\bin;$taskEfinity\pgm\bin;$taskEfinity\debugger\bin;$taskEfinity\scripts;$env:PATH"
}
$old=@{}
foreach($k in $vars.Keys) { $old[$k]=[Environment]::GetEnvironmentVariable($k,'Process'); [Environment]::SetEnvironmentVariable($k,$vars[$k],'Process') }
$positionPushed=$false
try {
    Push-Location (Split-Path -Parent $projectFile)
    $positionPushed=$true
    # Efinity 2026.1 catches ImportError and may report exit 0 after skipping PT.
    # Check its exact import before compile, then independently check artifacts.
    if ($Flow -ne 'map') {
        $preflightLog=Join-Path $logDir "efinity_${Project}_interface_preflight.log"
        $record.preflight_log=$preflightLog
        $oldPreference=$ErrorActionPreference
        $ErrorActionPreference='Continue'
        try {
            & (Join-Path $taskEfinity 'python311\bin\python.exe') -X utf8 (Join-Path $PSScriptRoot 'efinity_preflight.py') 2>&1 | Tee-Object -FilePath $preflightLog
            $preflightCode=$LASTEXITCODE
        } finally { $ErrorActionPreference=$oldPreference }
        $record.preflight_exit_code=$preflightCode
        if($preflightCode -ne 0) {
            throw "Interface Designer cannot load. Build stopped; no complete programming file verified. See $preflightLog"
        }
    }
    $record.stage='run_tool'
    $oldPreference=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    try {
        & $tool $projectFile --flow $Flow --timeout 1800 2>&1 | Tee-Object -FilePath $logFile
        $code=$LASTEXITCODE
    } finally { $ErrorActionPreference=$oldPreference }
    $record.exit_code=$code
    if ($code -ne 0) { throw "Efinity failed (exit=$code). See $logFile" }
    $record.stage='validate_results'
    [xml]$projectXml=Get-Content -LiteralPath $projectFile -Raw
    $designName=$projectXml.DocumentElement.GetAttribute('name')
    if(-not $designName){throw 'Project XML has no design name.'}
    $outDir=Join-Path (Split-Path -Parent $projectFile) 'outflow'
    $designLog=Join-Path $outDir "$designName.log"
    $record.design_log=$designLog
    if(-not (Test-Path -LiteralPath $designLog)){throw "Missing design log: $designLog"}
    if((Get-Item -LiteralPath $designLog).LastWriteTime -lt $runStart.AddSeconds(-2)){throw 'Design log is stale.'}
    $content=Get-Content -LiteralPath $designLog -Raw
    if($content -match 'Skipping Interface Designer|Failed to import Interface Designer|Missing Interface Designer LPF|no programming file will be generated'){
        throw "Tool skipped required Interface Designer/programming stages. Exit 0 is not sufficient. See $designLog"
    }
    if($Flow -eq 'compile'){
        # Placement/route iterations may report hold violations that are fixed later.
        # Accept only fresh, final STA summary rows, not intermediate log warnings.
        $timingFile=Join-Path $outDir "$designName.timing.rpt"
        if(-not(Test-Path -LiteralPath $timingFile)){throw 'Missing final timing report.'}
        if((Get-Item -LiteralPath $timingFile).LastWriteTime -lt $runStart.AddSeconds(-2)){throw 'Final timing report is stale.'}
        $timing=Get-Content -LiteralPath $timingFile -Raw
        $summary=[regex]::Match($timing,'(?s)Clock Relationship Summary \(begin\).*?Clock Relationship Summary \(end\)')
        if(-not $summary.Success){throw 'Final STA clock summary not found.'}
        $sections=$summary.Value -split 'Hold \(Min\) Clock Relationship'
        if($sections.Count -ne 2){throw 'Incomplete final setup/hold summary.'}
        $slackPattern='(?m)^\s*\S+\s+\S+\s+[-+]?\d+(?:\.\d+)?\s+([-+]?\d+(?:\.\d+)?)\s+\('
        $setupRows=[regex]::Matches($sections[0],$slackPattern)
        $holdRows=[regex]::Matches($sections[1],$slackPattern)
        if($setupRows.Count -eq 0 -or $holdRows.Count -eq 0){throw 'No final setup/hold timing rows.'}
        $culture=[System.Globalization.CultureInfo]::InvariantCulture
        $setup=@($setupRows | ForEach-Object {[double]::Parse($_.Groups[1].Value,$culture)})
        $hold=@($holdRows | ForEach-Object {[double]::Parse($_.Groups[1].Value,$culture)})
        $minSetup=($setup | Measure-Object -Minimum).Minimum
        $minHold=($hold | Measure-Object -Minimum).Minimum
        $record.final_sta=@{report=$timingFile;minimum_setup_slack_ns=$minSetup;minimum_hold_slack_ns=$minHold;scope='Declared vendor constraints only; physical board not measured'}
        if($minSetup -lt 0 -or $minHold -lt 0){throw "Final timing violations: setup=$minSetup ns, hold=$minHold ns. See $timingFile"}
    }
    $requiredArtifacts=@()
    if($Flow -eq 'map' -or $Flow -eq 'compile'){
        $requiredArtifacts+=Join-Path $outDir "$designName.map.v"
        $requiredArtifacts+=Join-Path $outDir "$designName.map.rpt"
    }
    if($Flow -ne 'map'){
        $lpfCandidates=@((Join-Path $outDir "$designName.lpf"),(Join-Path (Split-Path -Parent $projectFile) "$designName.lpf"))
        $freshLpf=@($lpfCandidates | Where-Object {
            (Test-Path -LiteralPath $_) -and (Get-Item -LiteralPath $_).Length -gt 0 -and (Get-Item -LiteralPath $_).LastWriteTime -ge $runStart.AddSeconds(-2)
        })
        if($freshLpf.Count -eq 0){throw 'No fresh Interface Designer LPF output. Pin configuration is not verified.'}
        $requiredArtifacts+=$freshLpf[0]
    }
    if($Flow -eq 'compile'){$requiredArtifacts+=Join-Path $outDir "$designName.hex"}
    foreach($artifact in $requiredArtifacts){
        if(-not (Test-Path -LiteralPath $artifact)){throw "Missing artifact: $artifact"}
        $info=Get-Item -LiteralPath $artifact
        if($info.Length -eq 0 -or $info.LastWriteTime -lt $runStart.AddSeconds(-2)){throw "Empty or stale artifact: $artifact"}
    }
    $record.artifacts=@($requiredArtifacts | ForEach-Object { @{path=$_;sha256=(Get-TaskFileSha256 -Path $_)} })
    $record.status='PASS'
    $record.stage='finished'
    Write-Host "VERIFIED: $Project $Flow (scope=$($record.scope)). Physical board testing remains pending."
} catch {
    $record.status='FAIL'
    $record.error=$_.Exception.Message
    throw
} finally {
    if($positionPushed) { Pop-Location }
    foreach($k in $old.Keys) { [Environment]::SetEnvironmentVariable($k,$old[$k],'Process') }
    $record.finished=(Get-Date).ToString('o')
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $statusFile -Encoding UTF8
}
