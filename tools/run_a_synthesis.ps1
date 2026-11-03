param()
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'file_hash.ps1')
$aRoot=Split-Path $PSScriptRoot -Parent
$aEfinity=Join-Path $aRoot 'tools\efinity\2026.1'
$aProject=Join-Path $aRoot 'projects\06_a_units\a_side_units.xml'
$aStatus=Join-Path $aRoot 'logs\a_side_synthesis.json'
$aLog=Join-Path $aRoot 'logs\a_side_synthesis.log'
$record=[ordered]@{status='RUNNING';scope='synthesis_only';started=(Get-Date).ToString('o');physical_board_programmed=$false;final_sta_verified=$false;project=$aProject}
$old=@{}
$vars=@{EFINITY_HOME=$aEfinity.Replace('\','/');EFXPT_HOME=($aEfinity+'/pt');PYTHONHOME=($aEfinity+'\python311');PYTHONUTF8='1';PATH=($aEfinity+'\python311\bin;'+$aEfinity+'\bin;'+$aEfinity+'\scripts;'+$env:PATH)}
$vars.EFINITY_USER_DIR_INI=(Join-Path $aRoot 'config\efinity_user\user_dir.ini').Replace('\','/')
$vars.EFXPGM_HOME=($aEfinity+'/pgm')
$vars.EFXDBG_HOME=($aEfinity+'/debugger')
$vars.EFXIPM_HOME=($aEfinity+'/ipm')
$vars.EFXSVF_HOME=($aEfinity+'/debugger/svf_player')
$record|ConvertTo-Json -Depth 8|Set-Content $aStatus -Encoding UTF8
try {
    foreach($k in $vars.Keys){$old[$k]=[Environment]::GetEnvironmentVariable($k,'Process');[Environment]::SetEnvironmentVariable($k,$vars[$k],'Process')}
    & (Join-Path $aEfinity 'python311\bin\python.exe') -X utf8 (Join-Path $PSScriptRoot 'prepare_a_units.py')
    if($LASTEXITCODE -ne 0){throw 'Prepare failed'}
    $aStart=Get-Date
    Push-Location (Split-Path $aProject -Parent)
    try {
        $ErrorActionPreference='Continue'
        & (Join-Path $aEfinity 'bin\efx_run.bat') $aProject --flow map --timeout 1800 2>&1 | Tee-Object -FilePath $aLog
        $aCode=$LASTEXITCODE
        $ErrorActionPreference='Stop'
    } finally {Pop-Location}
    if($aCode -ne 0){throw "Efinity exit $aCode"}
    $aFiles=@('a_side_units.map.v','a_side_units.map.rpt')|ForEach-Object {Join-Path (Split-Path $aProject -Parent) ('outflow\'+$_)}
    foreach($p in $aFiles){if(!(Test-Path $p) -or (Get-Item $p).Length -eq 0 -or (Get-Item $p).LastWriteTime -lt $aStart.AddSeconds(-2)){throw "Missing/stale synthesis result: $p"}}
    $record.artifacts=@($aFiles|ForEach-Object {@{file=$_;sha256=(Get-TaskFileSha256 -Path $_)}})
    $record.status='PASS'
} catch {$record.status='FAIL';$record.error=$_.Exception.Message;throw}
finally {
    foreach($k in $old.Keys){[Environment]::SetEnvironmentVariable($k,$old[$k],'Process')}
    $record.finished=(Get-Date).ToString('o');$record|ConvertTo-Json -Depth 8|Set-Content $aStatus -Encoding UTF8
}
