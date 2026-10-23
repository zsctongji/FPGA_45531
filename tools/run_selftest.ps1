param(
    [string]$VivadoPath = 'D:\Xilinx\Vivado\2018.3',
    [ValidateSet('auto','icarus','xsim')][string]$Backend = 'auto',
    [string]$IcarusPath = '',
    [ValidateSet('all','vision','events')][string]$Suite = 'all'
)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
if ($env:FPGA_VIVADO_ROOT) { $VivadoPath = $env:FPGA_VIVADO_ROOT }
if (-not $IcarusPath) { $IcarusPath = Join-Path $taskRoot 'tools\iverilog\bin' }
if ($env:FPGA_ICARUS_BIN) { $IcarusPath = $env:FPGA_ICARUS_BIN }
if ($Backend -eq 'auto') {
    if (Test-Path -LiteralPath (Join-Path $IcarusPath 'iverilog.exe')) { $Backend='icarus' }
    else { $Backend='xsim' }
}
$binPath = Join-Path $VivadoPath 'bin'
if ($Backend -eq 'icarus') { $binPath=$IcarusPath; $programs=@('iverilog.exe','vvp.exe') }
else { $programs=@('xvlog.bat','xelab.bat','xsim.bat') }
$visionSuite = @('tb_pixel_ops','tb_vision_stream','tb_sobel_3x3','tb_sobel_720p','tb_sensor_smooth','tb_sensor_frame_align','tb_video_display_preprocess')
$eventSuite = @('tb_frame_motion_stats','tb_multimodal_alarm','tb_video_motion_display','tb_motion_minimum','tb_motion_1080p')
$testTops = if ($Suite -eq 'vision') { $visionSuite } elseif ($Suite -eq 'events') { $eventSuite } else { $visionSuite + $eventSuite }
$rtlFiles = @(Get-ChildItem -LiteralPath (Join-Path $taskRoot 'rtl') -Filter '*.v' -File | Sort-Object Name | ForEach-Object FullName)
$logRoot = Join-Path $taskRoot 'logs'
$buildRoot = Join-Path $taskRoot 'build\selftest'
New-Item -ItemType Directory -Force -Path $logRoot,$buildRoot | Out-Null
# Invalidate old status before starting: an interrupted run cannot leave stale PASS.
$reportPath = Join-Path $logRoot $(if ($Suite -eq 'all') { 'selftest.json' } else { "selftest_${Suite}.json" })
$result = [ordered]@{
    suite_status = 'RUNNING'
    scope = 'Portable RTL functional simulation only; no Efinity build or board measurement'
    started_at = (Get-Date).ToString('o')
    backend = $Backend
    selected_suite = $Suite
    simulator_bin = $binPath
    tests = @()
}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
function Invoke-SimStep {
    param([string]$Executable, [string[]]$Arguments, [string]$Log)
    # XSim can return zero after a Verilog fatal, so also check transcript content.
    $oldPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $transcript = & $Executable @Arguments 2>&1 | Out-String
        $processCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $oldPreference }
    $transcript | Set-Content -LiteralPath $Log -Encoding UTF8
    if ($processCode -ne 0 -or $transcript -match '(?im)(\bFAIL\b|\bFATAL\b|^\s*ERROR:)') {
        throw "Simulation tool failed (exit=$processCode); inspect $Log"
    }
    return $transcript
}
try {
    . (Join-Path $PSScriptRoot 'file_hash.ps1')
    foreach ($program in $programs) {
        if (-not (Test-Path -LiteralPath (Join-Path $binPath $program))) {
            throw "Missing $program under $binPath. Use -VivadoPath or FPGA_VIVADO_ROOT."
        }
    }
    $result.rtl_sources = @($rtlFiles | ForEach-Object { [ordered]@{file=$_;sha256=(Get-TaskFileSha256 -Path $_)} })
    foreach ($top in $testTops) {
        Write-Host "Running $top ..."
        $testFile = Join-Path $taskRoot "sim\$top.sv"
        if (-not (Test-Path -LiteralPath $testFile)) { throw "Missing testbench $testFile" }
        $testBuild = Join-Path $buildRoot $top
        New-Item -ItemType Directory -Force -Path $testBuild | Out-Null
        Push-Location $testBuild
        try {
            if ($Backend -eq 'icarus') {
                $programImage = Join-Path $testBuild "$top.vvp"
                $null = Invoke-SimStep -Executable (Join-Path $binPath 'iverilog.exe') -Arguments (@('-g2012','-s',$top,'-o',$programImage) + $rtlFiles + @($testFile)) -Log (Join-Path $logRoot "$top.compile.log")
                $simulationText = Invoke-SimStep -Executable (Join-Path $binPath 'vvp.exe') -Arguments @($programImage) -Log (Join-Path $logRoot "$top.run.log")
            } else {
                $null = Invoke-SimStep -Executable (Join-Path $binPath 'xvlog.bat') -Arguments (@('-sv') + $rtlFiles + @($testFile)) -Log (Join-Path $logRoot "$top.compile.log")
                $null = Invoke-SimStep -Executable (Join-Path $binPath 'xelab.bat') -Arguments @($top,'-s',"${top}_snapshot",'-debug','typical') -Log (Join-Path $logRoot "$top.elaborate.log")
                $simulationText = Invoke-SimStep -Executable (Join-Path $binPath 'xsim.bat') -Arguments @("${top}_snapshot",'-runall') -Log (Join-Path $logRoot "$top.run.log")
            }
            if ($simulationText -notmatch ("PASS " + [regex]::Escape($top))) {
                throw "No expected PASS marker for $top; inspect its run log"
            }
            $markers = @($simulationText -split "`r?`n" | Where-Object { $_ -match '^PASS ' })
            $result.tests += [ordered]@{ name=$top; status='PASS'; evidence=$markers; testbench_sha256=(Get-TaskFileSha256 -Path $testFile) }
            Write-Host ($markers -join "`n")
        } finally { Pop-Location }
    }
    $result.suite_status = 'PASS'
    $result.finished_at = (Get-Date).ToString('o')
    Write-Host 'ALL PORTABLE RTL TESTS PASSED. This is not a board test.'
} catch {
    $result.suite_status = 'FAIL'
    $result.error = $_.Exception.Message
    $result.finished_at = (Get-Date).ToString('o')
    throw
} finally {
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
