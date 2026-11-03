param([ValidateSet('interface','map','pnr','sta_tclsh','pgm')][string[]]$Flows=@('interface','map','pnr'))
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$projectDir=Join-Path $taskRoot 'projects/10_soc_cold'
$efinity=Join-Path $taskRoot 'tools/efinity/2026.1'
$reportPath=Join-Path $taskRoot 'logs/soc_cold_build.json'
$record=[ordered]@{status='RUNNING';started=(Get-Date).ToString('o');scope='Full C7 private SPI RX corrected implementation, not a complete hardware release';board_programmed=$false;download_allowed=$false;steps=@();sources=@()}
$taskUserDir=Join-Path $taskRoot 'build/c7_live_20261101/efinity_user'
New-Item -ItemType Directory -Force -Path $taskUserDir | Out-Null
$taskUserIni=Join-Path $taskUserDir 'user_dir.ini'
@('[General]',('EFINITY_USER_DIR='+$taskUserDir.Replace('\','/'))) | Set-Content -LiteralPath $taskUserIni -Encoding ascii
$manifest=Get-Content -LiteralPath (Join-Path $projectDir 'PHYSICAL_MANIFEST.json') -Raw | ConvertFrom-Json
foreach($prop in $manifest.source_sha256.PSObject.Properties){
 $path=Join-Path $taskRoot $prop.Name
 $record.sources+=@{path=$prop.Name;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()}
}
foreach($name in @('soc_physical.peri.xml','soc_physical.sdc','soc_physical.xml','PHYSICAL_MANIFEST.json','soc_physical_cdc.sdc','review_timing.tcl')){
 if(-not (Test-Path -LiteralPath (Join-Path $projectDir $name))){continue}
 $record.sources+=@{path="projects/10_soc_cold/$name";sha256=(Get-FileHash -LiteralPath (Join-Path $projectDir $name) -Algorithm SHA256).Hash.ToLowerInvariant()}
}
function Save-Record {$record | ConvertTo-Json -Depth 9 | Set-Content -LiteralPath $reportPath -Encoding UTF8}
Save-Record
$vars=@{EFINITY_HOME=$efinity.Replace('\','/');EFXPT_HOME=($efinity+'/pt').Replace('\','/');EFXPGM_HOME=($efinity+'/pgm').Replace('\','/');PYTHONHOME=(Join-Path $efinity 'python311');PYTHONUTF8='1';EFINITY_USER_DIR_INI=$taskUserIni.Replace('\','/');PATH="$efinity/python311/bin;$efinity/bin;$efinity/scripts;$env:PATH"}
if([Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq 'X64' -and -not $env:PROCESSOR_ARCHITECTURE){$vars.PROCESSOR_ARCHITECTURE='AMD64'}
$old=@{};foreach($key in $vars.Keys){$old[$key]=[Environment]::GetEnvironmentVariable($key,'Process');[Environment]::SetEnvironmentVariable($key,$vars[$key],'Process')}
$pushed=$false
try {
 Push-Location $projectDir;$pushed=$true
 if($Flows -contains 'interface'){
  & (Join-Path $efinity 'python311/bin/python.exe') -X utf8 (Join-Path $taskRoot 'tools/efinity_preflight.py')
  if($LASTEXITCODE -ne 0){throw 'Interface Designer preflight failed; skipping is not accepted'}
 }
 foreach($flow in $Flows){
  if($flow -eq 'pnr' -or $flow -eq 'sta_tclsh'){
   & (Join-Path $efinity 'python311/bin/python.exe') -X utf8 (Join-Path $taskRoot 'tools/generate_soc_cold_cdc.py')
   if($LASTEXITCODE -ne 0){throw 'Mapped CDC constraint binding failed'}
  }
  $step=[ordered]@{flow=$flow;started=(Get-Date).ToString('o');status='RUNNING';log="logs/soc_cold_$flow.log"}
  if($flow -in @('sta_tclsh','pgm')){$step.routed_lbf_sha256=(Get-FileHash -LiteralPath (Join-Path $projectDir 'work_pnr/soc_physical.lbf') -Algorithm SHA256).Hash.ToLowerInvariant()}
  $step.constraints=@{}
  foreach($name in @('soc_physical.sdc','soc_physical_cdc.sdc','soc_physical_cdc_review.sdc','soc_physical.peri.xml','review_timing.tcl')){
   if(Test-Path -LiteralPath (Join-Path $projectDir $name)){$step.constraints[$name]=(Get-FileHash -LiteralPath (Join-Path $projectDir $name) -Algorithm SHA256).Hash.ToLowerInvariant()}
  }
  $record.steps+=,$step;Save-Record
  $ErrorActionPreference='Continue'
  $flowArgs=@((Join-Path $projectDir 'soc_physical.xml'),'--flow',$flow,'--timeout','1800')
  if($flow -eq 'sta_tclsh'){$flowArgs+=@('--tcl_script',(Join-Path $projectDir 'review_timing.tcl'))}
  & (Join-Path $efinity 'bin/efx_run.bat') @flowArgs 2>&1 | Tee-Object -FilePath (Join-Path $taskRoot $step.log)
  $code=$LASTEXITCODE;$ErrorActionPreference='Stop';$step.exit_code=$code;$step.finished=(Get-Date).ToString('o')
  if($code -ne 0){$step.status='FAIL';throw "Efinity $flow failed ($code)"}
  $text=Get-Content -LiteralPath (Join-Path $taskRoot $step.log) -Raw
  $expected=if($flow -eq 'interface'){'Interface|interface|pt'}else{$flow}
  if($text -match 'Skipping Interface Designer|Failed to import'){throw 'Interface Designer was skipped'}
  if($text -match 'Failed to run command|No bus skew paths found|Unable to generate slack report'){throw 'STA command/CDC report incomplete'}
  if($text -notmatch "$expected\s*:\s*PASS" -and $flow -notin @('interface','sta_tclsh')){throw "Missing $flow PASS"}
  if($flow -eq 'interface'){
   $lpf=Get-Item -LiteralPath (Join-Path $projectDir 'outflow/soc_physical.lpf') -ErrorAction Stop
   if($lpf.Length -eq 0 -or $lpf.LastWriteTime -lt [datetime]$step.started){throw 'Missing/stale interface LPF'}
  }
  if($flow -eq 'map' -or $flow -eq 'pnr'){
   $names=if($flow -eq 'map'){@('soc_physical.map.v','soc_physical.map.rpt')}else{@('soc_physical.timing.rpt')}
   foreach($name in $names){
    $file=Get-Item -LiteralPath (Join-Path $projectDir "outflow/$name") -ErrorAction Stop
    if($file.Length -eq 0 -or $file.LastWriteTime -lt [datetime]$step.started){throw "Missing/stale $name"}
   }
  }
  if($flow -eq 'sta_tclsh'){
   foreach($name in @('soc_physical.review_timing.rpt','soc_physical.bus_setup.rpt','soc_physical.bus_hold.rpt','soc_physical.clocks.rpt')){
    $file=Get-Item -LiteralPath (Join-Path $projectDir "outflow/$name") -ErrorAction Stop
    if($file.Length -eq 0 -or $file.LastWriteTime -lt [datetime]$step.started){throw "Missing/stale STA $name"}
   }
  }
  if($flow -eq 'pgm'){
   # Efinity's pgm flow converts the routed LBF to configuration files.
   # USB access is a separate 'program' flow, absent from this ValidateSet.
   $file=Get-Item -LiteralPath (Join-Path $projectDir 'outflow/soc_physical.hex') -ErrorAction Stop
   if($file.Length -eq 0 -or $file.LastWriteTime -lt [datetime]$step.started){throw 'Missing/stale generated configuration stream'}
   $step.configuration_sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  $step.status='PASS';Save-Record
  $phase=[ordered]@{status='PASS';completed_flow=$flow;started=$step.started;finished=$step.finished;scope=$record.scope;board_programmed=$false;download_allowed=$false;step=$step;sources=$record.sources}
  $phase | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $taskRoot "logs/soc_cold_${flow}_check.json") -Encoding UTF8
 }
 $record.status='PASS'
} catch {$record.status='FAIL';$record.error=$_.Exception.Message;if($record.steps.Count){$record.steps[-1].status='FAIL'};Write-Host $record.error}
finally {if($pushed){Pop-Location};foreach($key in $old.Keys){[Environment]::SetEnvironmentVariable($key,$old[$key],'Process')};$record.finished=(Get-Date).ToString('o');Save-Record}
if($record.status -ne 'PASS'){exit 1}
if($Flows -contains 'pnr'){Copy-Item -LiteralPath $reportPath -Destination (Join-Path $taskRoot 'logs/soc_cold_route_build.json') -Force}
Write-Host 'Tool flows passed. STA/CDC and physical release readiness require separate report review.'
