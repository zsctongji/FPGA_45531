param([switch]$RouteOnly)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$projectDir=Join-Path $taskRoot 'build/c9_sideband_seed3_image_20261103'
$efinity=Join-Path $taskRoot 'tools/efinity/2026.1'
$env:EFINITY_HOME=$efinity.Replace('\','/')
$env:EFXPT_HOME=($efinity+'/pt').Replace('\','/')
$env:EFXPGM_HOME=($efinity+'/pgm').Replace('\','/')
$env:PYTHONHOME=Join-Path $efinity 'python311'
$env:PYTHONUTF8='1'
$env:EFINITY_USER_DIR_INI=(Join-Path $taskRoot 'build/ddr_diag/efinity_user/user_dir.ini').Replace('\','/')
$env:PROCESSOR_ARCHITECTURE='AMD64'
$env:PATH="$efinity/python311/bin;$efinity/bin;$efinity/scripts;$env:PATH"
Push-Location $projectDir
try {
 & "$efinity/python311/bin/python.exe" -X utf8 (Join-Path $taskRoot 'tools/efinity_preflight.py')
 if($LASTEXITCODE -ne 0){throw 'Interface Designer cannot load'}
 $flows=if($RouteOnly){@('pnr','sta_tclsh','pgm')}else{@('interface','map','pnr','sta_tclsh','pgm')}
 foreach($flow in $flows) {
  if($flow -in @('pnr','sta_tclsh')) {
   & "$efinity/python311/bin/python.exe" -X utf8 (Join-Path $projectDir 'bind_cdc.py')
   if($LASTEXITCODE -ne 0){throw 'CDC binding failed'}
  }
  $flowArgs=@((Join-Path $projectDir 'soc_physical.xml'),'--flow',$flow,'--timeout','1800')
  if($flow -eq 'sta_tclsh'){$flowArgs+=@('--tcl_script',(Join-Path $projectDir 'review_timing.tcl'))}
  $ErrorActionPreference='Continue'
  & "$efinity/bin/efx_run.bat" @flowArgs 2>&1 | Tee-Object -FilePath (Join-Path $projectDir ($flow+'.log'))
  $code=$LASTEXITCODE;$ErrorActionPreference='Stop'
  if($code -ne 0){throw "Diagnostic $flow failed ($code)"}
  $text=Get-Content -LiteralPath (Join-Path $projectDir ($flow+'.log')) -Raw
  if($text -match 'Failed to run command|No bus skew paths found|Unable to generate slack report|Skipping Interface Designer'){throw "Incomplete diagnostic $flow"}
  if($flow -notin @('interface','sta_tclsh') -and $text -notmatch "\b$flow\s*:\s*PASS\b"){throw "Missing diagnostic $flow PASS"}
 }
} finally {Pop-Location}
Write-Host 'Diagnostic flows completed; source, pin and timing audit required before SRAM use.'
