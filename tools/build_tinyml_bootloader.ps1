$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'file_hash.ps1')
$root=Split-Path -Parent $PSScriptRoot
$gccRoot=Join-Path $root 'tools\riscv_gcc\13.4.0'
$makeRoot=Join-Path $root 'tools\windows_build_tools\4.4.1'
$soc=Join-Path $root 'projects\03_tinyml\embedded_sw\sapphire_soc_tinyml'
$app=Join-Path $soc 'software\standalone\bootloader'
$header=Join-Path $soc 'bsp\efinix\EfxSapphireSoc\app\bootloaderConfig.h'
$text=[IO.File]::ReadAllText($header)
$text=[regex]::Replace($text,'(#define USER_SOFTWARE_SIZE\s+)0x[0-9a-fA-F]+','${1}0x00400000')
[IO.File]::WriteAllText($header,$text,(New-Object Text.UTF8Encoding($false)))
$log=Join-Path $root 'logs\bootloader_build.log'
$status=Join-Path $root 'logs\bootloader_build.json'
$record=[ordered]@{status='RUNNING';started=(Get-Date).ToString('o');scope='Cross compilation and ROM lane generation only';flash_offset='0x00380000';application_ram_address='0x00001000';application_copy_capacity=4194304;board_programmed=$false}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $status -Encoding UTF8
$oldPath=$env:PATH
$pushed=$false
try {
    $env:PATH="$gccRoot\bin;$makeRoot\bin;$oldPath"
    $prefix=(Join-Path $gccRoot 'bin\riscv-none-elf-').Replace('\','/')
    Push-Location $app; $pushed=$true
    $args=@('-B','all','BSP=efinix/EfxSapphireSoc','OBJDIR=build_ours',"RISCV_BIN=$prefix",'DEBUG=no','BENCH=no','MARCH=rv32im_zicsr_zifencei','MABI=ilp32','CFLAGS_ARGS=-DNO_LIBC_INIT_ARRAY -ffunction-sections -fdata-sections','LIBS=-Wl,--gc-sections')
    $oldPreference=$ErrorActionPreference; $ErrorActionPreference='Continue'
    try {& (Join-Path $makeRoot 'bin\make.exe') @args 2>&1 | Out-File -LiteralPath $log -Encoding UTF8; $code=$LASTEXITCODE} finally {$ErrorActionPreference=$oldPreference}
    if($code -ne 0){throw "Bootloader build failed (exit=$code); see $log"}
    $file=Join-Path $app 'build_ours\bootloader.bin'
    $bytes=[IO.File]::ReadAllBytes($file)
    if($bytes.Length -gt 4096 -or $bytes.Length -eq 0){throw "Bootloader must fit the 4096-byte RAM; actual=$($bytes.Length)"}
    $record.binary_bytes=$bytes.Length
    $record.binary_sha256=Get-TaskFileSha256 -Path $file
    $ip=Join-Path $root 'projects\03_tinyml\ip\sapphire_soc'
    $backup=Join-Path $root 'projects\03_tinyml\original_bootrom'
    New-Item -ItemType Directory -Force -Path $backup | Out-Null
    $record.lanes=@()
    for($lane=0;$lane -lt 4;$lane++){
        $name="EfxSapphireSoc.v_toplevel_system_ramA_logic_ram_symbol$lane.bin"
        $target=Join-Path $ip $name
        if(-not(Test-Path -LiteralPath (Join-Path $backup $name))){Copy-Item -LiteralPath $target -Destination (Join-Path $backup $name)}
        $lines=New-Object 'System.Collections.Generic.List[string]'
        for($word=0;$word -lt 1024;$word++){
            $index=4*$word+$lane
            $value=if($index -lt $bytes.Length){$bytes[$index]}else{0}
            $lines.Add([Convert]::ToString($value,2).PadLeft(8,'0'))
        }
        [IO.File]::WriteAllLines($target,$lines,(New-Object Text.UTF8Encoding($false)))
        $record.lanes+=@{path=$target;sha256=(Get-TaskFileSha256 -Path $target);lines=1024}
    }
    $record.status='PASS'
    Write-Host "BOOTLOADER BUILT: $($bytes.Length) bytes, copies up to 4 MiB from Flash 0x380000. FPGA must be recompiled."
} catch {$record.status='FAIL';$record.error=$_.Exception.Message;throw}
finally {if($pushed){Pop-Location};$env:PATH=$oldPath;$record.finished=(Get-Date).ToString('o');$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $status -Encoding UTF8}
