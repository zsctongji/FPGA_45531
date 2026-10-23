param(
    [string]$VivadoBin = 'D:\Xilinx\Vivado\2018.3\bin',
    [string]$BuildDirectory = (Join-Path $PSScriptRoot '..\work\core_sim')
)
$ErrorActionPreference = 'Stop'
$packageRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$buildPath = [IO.Path]::GetFullPath($BuildDirectory)
foreach ($toolName in @('xvlog', 'xelab', 'xsim')) {
    if (-not (Test-Path -LiteralPath (Join-Path $VivadoBin "$toolName.bat"))) {
        throw "Missing Vivado simulator: $VivadoBin\$toolName.bat"
    }
}
New-Item -ItemType Directory -Path $buildPath -Force | Out-Null
$sourceFiles = @(
    (Join-Path $packageRoot 'rtl\rgb888_to_gray.v'),
    (Join-Path $packageRoot 'rtl\gray_threshold.v'),
    (Join-Path $packageRoot 'rtl\sobel_stream.v'),
    (Join-Path $packageRoot 'rtl\portable_vision_core.v'),
    (Join-Path $packageRoot 'sim\tb_pixel_ops.sv'),
    (Join-Path $packageRoot 'sim\tb_vision_stream.sv'),
    (Join-Path $packageRoot 'sim\tb_sobel_3x3.sv'),
    (Join-Path $packageRoot 'sim\tb_sobel_720p.sv')
)
Push-Location $buildPath
try {
    & (Join-Path $VivadoBin 'xvlog.bat') --sv @sourceFiles
    if ($LASTEXITCODE -ne 0) { throw 'xvlog compilation failed' }
    foreach ($testName in @('tb_pixel_ops', 'tb_vision_stream', 'tb_sobel_3x3', 'tb_sobel_720p')) {
        $snapshotName = "${testName}_snapshot"
        & (Join-Path $VivadoBin 'xelab.bat') $testName -s $snapshotName
        if ($LASTEXITCODE -ne 0) { throw "xelab failed: $testName" }
        $testLog = Join-Path $buildPath "$testName.log"
        & (Join-Path $VivadoBin 'xsim.bat') $snapshotName -runall -log $testLog
        if ($LASTEXITCODE -ne 0) { throw "xsim failed: $testName" }
        $logContent = Get-Content -LiteralPath $testLog -Raw
        if ($logContent -notmatch "PASS $testName`:" -or $logContent -match '(?m)^Fatal:|\$fatal') {
            throw "Test did not PASS: $testName; inspect $testLog"
        }
    }
    Write-Output "PASS all portable vision RTL tests. Logs: $buildPath"
} finally {
    Pop-Location
}
