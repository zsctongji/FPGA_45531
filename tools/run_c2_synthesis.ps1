param([ValidateSet('boundary','vendor','native')][string]$Target='boundary')
$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$projectDir=Join-Path $taskRoot 'projects\06_soc_c2'
$buildName=@{boundary='c2_boundary';vendor='c2_vendor';native='c2_native'}[$Target]
$topName=@{boundary='c2_system_boundary';vendor='c2_vendor_attachment';native='c2_tinyml_soc_top'}[$Target]
if($Target -eq 'native') {$projectDir=Join-Path $projectDir 'integration'}
$xmlName="$buildName.xml"
if($Target -eq 'vendor') {
    [xml]$vendorXml=Get-Content -LiteralPath (Join-Path $projectDir 'c2_boundary.xml') -Raw
    $vendorXml.project.SetAttribute('name',$buildName)
    $vendorXml.project.design_info.top_module.SetAttribute('name',$topName)
    foreach($rtlFile in Get-ChildItem -LiteralPath (Join-Path $projectDir 'rtl') -Filter *.sv) {
        if(-not ($vendorXml.project.design_info.design_file | Where-Object {$_.name -eq "rtl/$($rtlFile.Name)"})) {
            $element=$vendorXml.CreateElement('efx','design_file','http://www.efinixinc.com/enf_proj')
            $element.SetAttribute('name',"rtl/$($rtlFile.Name)");$element.SetAttribute('version','default');$element.SetAttribute('library','default')
            $vendorXml.project.design_info.AppendChild($element) | Out-Null
        }
    }
    $vendorXml.Save((Join-Path $projectDir $xmlName))
}
$efinity=Join-Path $taskRoot 'tools\efinity\2026.1'
$reportName=if($Target -eq 'boundary'){'c2_synthesis'}else{"c2_${Target}_synthesis"}
$statusPath=Join-Path $taskRoot "logs\$reportName.json"
$logPath=Join-Path $taskRoot "logs\$reportName.log"
$started=Get-Date
[xml]$projectXmlBefore=Get-Content -LiteralPath (Join-Path $projectDir $xmlName) -Raw
$record=[ordered]@{
    status='RUNNING'; started=$started.ToString('o'); scope='C2 boundary logic synthesis only'
    project=(Join-Path $projectDir $xmlName); top=$topName; target=$Target; device='Ti60F225'
    physical_board_programmed=$false; board_test_passed=$false; full_soc_integrated=$false
    timing_or_cdc_signoff=$false; artifacts=@(); sources=@()
}
$sourceFiles=@((Get-Item -LiteralPath (Join-Path $projectDir $xmlName)))+(Get-ChildItem -LiteralPath (Join-Path $taskRoot 'projects\06_soc_c2\rtl') -Filter *.sv)
if($Target -eq 'native') {
    $manifest=Get-Content -LiteralPath (Join-Path $projectDir 'INTEGRATION_MANIFEST.json') -Raw | ConvertFrom-Json
    foreach($property in $manifest.sources.PSObject.Properties) {$sourceFiles+=Get-Item -LiteralPath (Join-Path $taskRoot $property.Name)}
    $sourceFiles+=Get-ChildItem -LiteralPath $projectDir -Filter *.bin
}
foreach($file in $sourceFiles | Sort-Object FullName -Unique) {
    $record.sources+=@{path=$file.FullName;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
$vars=@{
    EFINITY_HOME=$efinity.Replace('\','/'); EFXPT_HOME=($efinity+'/pt').Replace('\','/')
    PYTHONHOME=(Join-Path $efinity 'python311'); PYTHONUTF8='1'
    EFINITY_USER_DIR_INI=(Join-Path $taskRoot 'config\efinity_user\user_dir.ini').Replace('\','/')
    PATH="$efinity\python311\bin;$efinity\bin;$efinity\scripts;$env:PATH"
}
$old=@{}
foreach($key in $vars.Keys) {
    $old[$key]=[Environment]::GetEnvironmentVariable($key,'Process')
    [Environment]::SetEnvironmentVariable($key,$vars[$key],'Process')
}
$pushed=$false
try {
    Push-Location $projectDir; $pushed=$true
    $ErrorActionPreference='Continue'
    & (Join-Path $efinity 'bin\efx_run.bat') (Join-Path $projectDir $xmlName) --flow map --timeout 600 2>&1 | Tee-Object -FilePath $logPath
    $code=$LASTEXITCODE
    $ErrorActionPreference='Stop'
    $record.exit_code=$code
    if($code -ne 0) { throw "Efinity synthesis exited $code; see $logPath" }
    $contents=Get-Content -LiteralPath $logPath -Raw
    if($contents -notmatch 'map\s*:\s*PASS') { throw "Efinity did not report map PASS; see $logPath" }
    foreach($name in @("$buildName.map.v","$buildName.map.rpt")) {
        $fresh=Get-Item -LiteralPath (Join-Path $projectDir "outflow\$name")
        if($fresh.Length -eq 0 -or $fresh.LastWriteTime -lt $started.AddSeconds(-2)) {throw "Missing/stale $name"}
    }
    $warningPath=Join-Path $projectDir "outflow\$buildName.warn.log"
    $warnings=Get-Content -LiteralPath $warningPath -Raw
    # Efinity appends warnings across map runs. Review only this run's section;
    # the full historical log remains on disk for traceability.
    $section=$warnings.LastIndexOf('// Efinity Synthesis Started')
    if($section -ge 0) {$warnings=$warnings.Substring($section)}
    $record.warnings=@([regex]::Matches($warnings,'(?s)\[EFX-.*?(?=\[EFX-|\z)') | ForEach-Object { $_.Value.Replace("`r",'').Replace("`n",'').Trim() })
    $reviewWarnings=$warnings
    if($Target -eq 'native') {
        $record.warning_scope='Full native warnings retained; portable C2 warnings checked strictly; inherited vendor warnings require review'
        $reviewWarnings=($record.warnings | Where-Object {$_ -match '06_soc_c2[\\/]rtl'}) -join "`n"
    }
    if($reviewWarnings -match 'VERI-WARNING|(?i:latch|undriven|multiple drivers)') {throw 'Review synthesis width/latch/driver warning before accepting this build'}
    if($Target -eq 'native') {
        $newCritical=@($record.warnings | Where-Object {$_ -match 'integration[\\/]c2_tinyml_soc_top' -and $_ -match 'does not have a driver|actual bit length|expression size|latch|multiple drivers'})
        if($newCritical.Count) {throw ('Native overlay contains unresolved driver/width/latch warnings: '+($newCritical -join '; '))}
    }
    $resourceText=Get-Content -LiteralPath (Join-Path $projectDir "outflow\$buildName.map.rpt") -Raw
    $record.resources=@{}
    foreach($kind in @('EFX_LUT4','EFX_FF','EFX_DSP48','EFX_ADD','EFX_RAM10')) {
        $matches=[regex]::Matches($resourceText,"$kind\s*:\s*(\d+)")
        if($matches.Count) {$record.resources[$kind]=[int]$matches[$matches.Count-1].Groups[1].Value}
    }
    $artifacts=Get-ChildItem -LiteralPath (Join-Path $projectDir 'outflow') -File | Where-Object { $_.Name -match '\.(v|db|rpt|json)$' -and $_.LastWriteTime -ge $started.AddSeconds(-2) }
    if(-not $artifacts) { throw 'No fresh synthesis artifacts found' }
    foreach($file in $artifacts) {
        $record.artifacts+=@{path=$file.FullName;bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
    }
    foreach($source in $record.sources) {
        $afterHash=(Get-FileHash -LiteralPath $source.path -Algorithm SHA256).Hash.ToLowerInvariant()
        if($afterHash -ne $source.sha256) {
            if($source.path.EndsWith($xmlName)) {
                # Efinity serializes XML itself (e.g. removes the XML declaration).
                # Accept formatting only; semantic source changes still fail.
                [xml]$projectXmlAfter=Get-Content -LiteralPath $source.path -Raw
                if($projectXmlAfter.DocumentElement.OuterXml -ne $projectXmlBefore.DocumentElement.OuterXml) {throw 'Project configuration changed during synthesis'}
                $source.post_tool_sha256=$afterHash
            } else {throw "Source changed during synthesis: $($source.path)"}
        }
    }
    $record.status='PASS'
} catch {
    $record.status='FAIL';$record.error=$_.Exception.Message
    Write-Host $record.error
} finally {
    if($pushed) {Pop-Location}
    foreach($key in $old.Keys) {[Environment]::SetEnvironmentVariable($key,$old[$key],'Process')}
    $record.finished=(Get-Date).ToString('o')
    $record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statusPath -Encoding UTF8
}
if($record.status -ne 'PASS') {exit 1}
Write-Host "PASS C2 $Target synthesis. Physical DDR, timing, CDC and board integration remain unverified."
