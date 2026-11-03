$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$gccRoot=Join-Path $taskRoot 'tools\riscv_gcc\13.4.0'
$taskOut=Join-Path $taskRoot 'build\c4\riscv'
$taskStatus=Join-Path $taskRoot 'logs\c4_riscv_compile.json'
$taskLog=Join-Path $taskRoot 'logs\c4_riscv_compile.log'
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$record=[ordered]@{status='RUNNING';scope='RV32 C4/C3 adapter object compilation only; not linked firmware or board execution';artifacts=@();board_inference_passed=$false}
$oldPath=$env:PATH
try {
    $env:PATH="$gccRoot\bin;$gccRoot\libexec\gcc\riscv-none-elf\13.4.0;$gccRoot\riscv-none-elf\bin;$oldPath"
    $app=Join-Path $taskRoot 'projects\03_tinyml\embedded_sw\sapphire_soc_tinyml\software\standalone\tinyml_pdti8\src'
    $includes=@("-I$taskRoot\team_work\shared\include","-I$taskRoot\team_work\03_ai_soc\c4","-I$taskRoot\team_work\03_ai_soc\c3_hal","-I$app","-I$app\tensorflow\third_party\flatbuffers\include","-I$app\tensorflow\third_party\gemmlowp")
    $flags=@('-c','-g0','-Os','-march=rv32im_zicsr_zifencei','-mabi=ilp32')
    [System.IO.File]::WriteAllText($taskLog,'')
    foreach($source in @('team_work\shared\src\cooperation_v1.c','team_work\03_ai_soc\c4\c4_bridge.c','team_work\03_ai_soc\c3_hal\c3_hal.c','team_work\03_ai_soc\c3_hal\c3_replay.c','team_work\03_ai_soc\c4\c4_tflm_adapter.cc')) {
        $file=Join-Path $taskRoot $source
        $obj=Join-Path $taskOut ([System.IO.Path]::GetFileNameWithoutExtension($source)+'.o')
        $compiler=Join-Path $gccRoot 'bin\riscv-none-elf-gcc.exe'
        $language=@('-std=c11','-Wall','-Wextra','-Werror')
        if($source.EndsWith('.cc')){
            $compiler=Join-Path $gccRoot 'bin\riscv-none-elf-g++.exe'
            $language=@('-std=c++11','-fno-exceptions','-fno-rtti')
        }
        $oldPreference=$ErrorActionPreference
        $ErrorActionPreference='Continue'
        try { & $compiler @flags @language @includes $file '-o' $obj 2>&1 | Out-File -LiteralPath $taskLog -Append -Encoding UTF8; $taskCode=$LASTEXITCODE } finally {$ErrorActionPreference=$oldPreference}
        if($taskCode -ne 0){throw "Object compilation failed: $source (exit=$taskCode)"}
        $record.artifacts+=@{source=$source;source_sha256=(Get-FileHash -LiteralPath $file).Hash;object=$obj;bytes=(Get-Item -LiteralPath $obj).Length;sha256=(Get-FileHash -LiteralPath $obj).Hash}
    }
    $record.status='PASS'
} catch {
    $record.status='FAIL';$record.error=$_.Exception.Message;throw
} finally {
    $env:PATH=$oldPath
    $record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $taskStatus -Encoding UTF8
}
Write-Host 'PASS: C4/C3 RISC-V compile checks; no firmware linked or board run.'

