param([ValidateRange(1,8)][int]$Jobs=2)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'file_hash.ps1')
$taskRoot=Split-Path -Parent $PSScriptRoot
$gccRoot=Join-Path $taskRoot 'tools\riscv_gcc\13.4.0'
$makeRoot=Join-Path $taskRoot 'tools\windows_build_tools\4.4.1'
$make=Join-Path $makeRoot 'bin\make.exe'
$gcc=Join-Path $gccRoot 'bin\riscv-none-elf-gcc.exe'
$app=Join-Path $taskRoot 'projects\03_tinyml\embedded_sw\sapphire_soc_tinyml\software\standalone\tinyml_pdti8'
$logDir=Join-Path $taskRoot 'logs'
$logFile=Join-Path $logDir 'firmware_person_detect.log'
$statusFile=Join-Path $logDir 'firmware_person_detect.json'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$start=Get-Date
$record=[ordered]@{status='RUNNING';started=$start.ToString('o');scope='Cross compilation of vendor static-image TinyML demo; no inference executed';project=$app;board_programmed=$false;board_inference_passed=$false}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusFile -Encoding UTF8
$oldPath=$env:PATH
$pushed=$false
try {
    foreach($file in @($make,$gcc,(Join-Path $app 'makefile'))){if(-not(Test-Path -LiteralPath $file)){throw "Missing dependency: $file"}}
    $env:PATH="$gccRoot\bin;$makeRoot\bin;$oldPath"
    $oldPreference=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    try {$compilerVersion=& $gcc --version 2>&1 | Out-String; $versionCode=$LASTEXITCODE} finally {$ErrorActionPreference=$oldPreference}
    if($versionCode -ne 0 -or $compilerVersion -notmatch '13\.4\.0'){throw 'RISC-V GCC cannot launch or version differs.'}
    $record.compiler=$compilerVersion.Trim()
    Push-Location $app
    $pushed=$true
    $prefix=(Join-Path $gccRoot 'bin\riscv-none-elf-').Replace('\','/')
    $targetArgs=@('-march=rv32im_zicsr_zifencei','-mabi=ilp32')
    $crtBegin=(& $gcc @targetArgs '-print-file-name=crtbegin.o' | Out-String).Trim().Replace('\','/')
    $crtEnd=(& $gcc @targetArgs '-print-file-name=crtend.o' | Out-String).Trim().Replace('\','/')
    foreach($file in @($crtBegin,$crtEnd)){if(-not(Test-Path -LiteralPath $file)){throw "Missing C++ CRT support: $file"}}
    $record.cpp_runtime_objects=@($crtBegin,$crtEnd)
    # GCC 13 uses separate ISA extensions for CSR/fence instructions present in this SoC.
    # Build in a new folder to avoid the vendor's precompiled build/ objects.
    # Custom startup is preserved; standard CRT objects supply C++ DSO/constructor metadata.
    $args=@("-j$Jobs",'-B','all','BSP=efinix/EfxSapphireSoc','OBJDIR=build_ours',"RISCV_BIN=$prefix","RISCV_CXX=${prefix}g++",'MARCH=rv32im_zicsr_zifencei','MABI=ilp32',"LIBS=$crtBegin ../common/tinyml_lib.a $crtEnd")
    Write-Host 'Compiling the static-image TinyML person-detection demo ...'
    $ErrorActionPreference='Continue'
    try {& $make @args 2>&1 | Out-File -LiteralPath $logFile -Encoding UTF8; $code=$LASTEXITCODE} finally {$ErrorActionPreference=$oldPreference}
    $record.exit_code=$code
    if($code -ne 0){throw "Firmware build failed (exit=$code). See $logFile"}
    $outputs=@('tinyml_pdti8.elf','tinyml_pdti8.hex','tinyml_pdti8.bin','tinyml_pdti8.map')
    $record.artifacts=@()
    foreach($name in $outputs){
        $file=Join-Path $app "build_ours\$name"
        if(-not(Test-Path -LiteralPath $file)){throw "Missing firmware output: $file"}
        $info=Get-Item -LiteralPath $file
        if($info.Length -eq 0 -or $info.LastWriteTime -lt $start.AddSeconds(-2)){throw "Empty/stale firmware output: $file"}
        $record.artifacts+=@{path=$file;bytes=$info.Length;sha256=(Get-TaskFileSha256 -Path $file)}
    }
    $elf=Join-Path $app 'build_ours\tinyml_pdti8.elf'
    if((Get-Item -LiteralPath (Join-Path $app 'build_ours\tinyml_pdti8.bin')).Length -gt 4194304){throw 'Application exceeds the 4 MiB bootloader copy capacity.'}
    $inspection=& (Join-Path $gccRoot 'bin\riscv-none-elf-readelf.exe') -h -A $elf 2>&1 | Out-String
    $inspectCode=$LASTEXITCODE
    $inspection | Set-Content -LiteralPath (Join-Path $logDir 'firmware_person_detect_elf.txt') -Encoding UTF8
    if($inspectCode -ne 0 -or $inspection -notmatch 'ELF32' -or $inspection -notmatch 'Machine:\s+RISC-V' -or $inspection -notmatch 'Entry point address:\s+0x1000'){
        throw 'Unexpected firmware architecture or entry address; inspect ELF report.'
    }
    $record.elf_verified='ELF32 RISC-V, entry 0x1000, vendor BSP'
    $deliverDir=Join-Path $taskRoot 'firmware\static_person_detect'
    New-Item -ItemType Directory -Force -Path $deliverDir | Out-Null
    foreach($name in $outputs){Copy-Item -LiteralPath (Join-Path $app "build_ours\$name") -Destination (Join-Path $deliverDir $name) -Force}
    $record.deliver_directory=$deliverDir
    $record.status='PASS'
    Write-Host "FIRMWARE BUILD PASSED. This is a compiled static-image demo, not live camera/board verification. See $statusFile"
} catch {
    $record.status='FAIL'
    $record.error=$_.Exception.Message
    throw
} finally {
    if($pushed){Pop-Location}
    $env:PATH=$oldPath
    $record.finished=(Get-Date).ToString('o')
    $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusFile -Encoding UTF8
}
