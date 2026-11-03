param([ValidateSet('interface','map','pnr','pgm')][string[]]$Flows=@('interface','map','pnr','pgm'))
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$projectDir=Join-Path $taskRoot 'projects/08_ddr_diag'
$efinity=Join-Path $taskRoot 'tools/efinity/2026.1'
$manifest=Get-Content -LiteralPath (Join-Path $projectDir 'DIAG_MANIFEST.json') -Raw | ConvertFrom-Json
$record=[ordered]@{status='RUNNING';started=(Get-Date).ToString('o');board_programmed=$false;scope='Offline standalone destructive DDR diagnostic generation';sources=@();steps=@()}
foreach($p in $manifest.source_sha256.PSObject.Properties){
 $actual=(Get-FileHash -LiteralPath (Join-Path $taskRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant()
 if($actual -ne $p.Value){throw ('Changed prepared input '+$p.Name)}
 $record.sources+=@{path=$p.Name;sha256=$actual}
}
$iniDir=Join-Path $taskRoot 'build/ddr_diag/efinity_user';New-Item -ItemType Directory -Force -Path $iniDir | Out-Null
$ini=Join-Path $iniDir 'user_dir.ini';@('[General]',('EFINITY_USER_DIR='+$iniDir.Replace('\','/'))) | Set-Content -LiteralPath $ini -Encoding ascii
$vars=@{EFINITY_HOME=$efinity.Replace('\','/');EFXPT_HOME=($efinity+'/pt').Replace('\','/');EFXPGM_HOME=($efinity+'/pgm').Replace('\','/');PYTHONHOME=(Join-Path $efinity 'python311');PYTHONUTF8='1';EFINITY_USER_DIR_INI=$ini.Replace('\','/');PATH="$efinity/python311/bin;$efinity/bin;$efinity/scripts;$env:PATH"}
if([Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq 'X64' -and -not $env:PROCESSOR_ARCHITECTURE){$vars.PROCESSOR_ARCHITECTURE='AMD64'}
$old=@{};foreach($k in $vars.Keys){$old[$k]=[Environment]::GetEnvironmentVariable($k,'Process');[Environment]::SetEnvironmentVariable($k,$vars[$k],'Process')}
function Save-Record {$record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $taskRoot 'logs/ddr_diag_build.json') -Encoding UTF8}
$pushed=$false
try {
 Push-Location $projectDir;$pushed=$true;Save-Record
 if($Flows -contains 'interface'){
  & (Join-Path $efinity 'python311/bin/python.exe') -X utf8 (Join-Path $taskRoot 'tools/efinity_preflight.py')
  if($LASTEXITCODE -ne 0){throw 'Interface import failed'}
 }
 foreach($flow in $Flows){
  $step=[ordered]@{flow=$flow;status='RUNNING';started=(Get-Date).ToString('o');inputs=@{}}
  foreach($n in @('ddr_diag.xml','ddr_diag.peri.xml','ddr_diag.sdc')){$step.inputs[$n]=(Get-FileHash -LiteralPath $n -Algorithm SHA256).Hash.ToLowerInvariant()}
  if($flow -eq 'pgm'){
   & (Join-Path $efinity 'python311/bin/python.exe') -X utf8 (Join-Path $taskRoot 'tools/check_ddr_diag.py') --timing-only
   if($LASTEXITCODE -ne 0){throw 'Timing check failed; no image generated'}
   $step.routed_lbf_sha256=(Get-FileHash -LiteralPath 'work_pnr/ddr_diag.lbf' -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  $record.steps+=,$step;Save-Record
  $ErrorActionPreference='Continue'
  & (Join-Path $efinity 'bin/efx_run.bat') (Join-Path $projectDir 'ddr_diag.xml') --flow $flow --timeout 1800 2>&1 | Tee-Object -FilePath (Join-Path $taskRoot "logs/ddr_diag_$flow.log")
  $code=$LASTEXITCODE;$ErrorActionPreference='Stop'
  if($code -ne 0){throw "Efinity $flow failed ($code)"}
  $log=Get-Content -LiteralPath (Join-Path $taskRoot "logs/ddr_diag_$flow.log") -Raw
  if($log -match 'Skipping Interface Designer|Failed to import|Skipping Export Bitstream'){throw 'Required stage skipped'}
  if($flow -ne 'interface' -and $log -notmatch "$flow\s*:\s*PASS"){throw "Missing $flow PASS"}
  $names=switch($flow){'interface'{@('ddr_diag.lpf')};'map'{@('ddr_diag.map.v','ddr_diag.map.rpt')};'pnr'{@('ddr_diag.timing.rpt')};'pgm'{@('ddr_diag.bit','ddr_diag.hex')}}
  $step.artifacts=@{}
  foreach($n in $names){$f=Get-Item -LiteralPath (Join-Path $projectDir "outflow/$n");if($f.Length -eq 0 -or $f.LastWriteTime -lt [datetime]$step.started){throw "Missing/stale $n"};$step.artifacts[$n]=(Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
  $step.status='PASS';$step.finished=(Get-Date).ToString('o');Save-Record
 }
 foreach($s in $record.sources){if((Get-FileHash -LiteralPath (Join-Path $taskRoot $s.path) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $s.sha256){throw ('Source changed during compilation: '+$s.path)}}
 $record.status='PASS'
} catch {$record.status='FAIL';$record.error=$_.Exception.Message;Write-Host $record.error}
finally {if($pushed){Pop-Location};foreach($k in $old.Keys){[Environment]::SetEnvironmentVariable($k,$old[$k],'Process')};$record.finished=(Get-Date).ToString('o');Save-Record}
if($record.status -ne 'PASS'){exit 1}
Write-Host 'PASS offline diagnostic build. Board execution remains unverified.'
