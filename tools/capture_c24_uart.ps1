param(
    [Parameter(Mandatory=$true)][ValidatePattern('^COM[1-9][0-9]*$')][string]$Port,
    [ValidateRange(1,600)][int]$Seconds=180,
    [switch]$BoardPortConfirmed,
    [string]$Manifest
)
$ErrorActionPreference='Stop'
if(-not $BoardPortConfirmed){throw 'Confirm the physical board UART and pass -BoardPortConfirmed before opening a serial port.'}
$taskRoot=Split-Path -Parent $PSScriptRoot
if(-not $Manifest){$Manifest=Join-Path $taskRoot 'firmware\c24_frame_person_detect\C24_INPUT_MANIFEST.json'}
$manifestFile=Get-Item -LiteralPath $Manifest
$inputRecord=Get-Content -LiteralPath $manifestFile.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
$logDir=Join-Path $taskRoot 'logs\c24'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp=(Get-Date -Format 'yyyyMMdd_HHmmss_fff')+'_'+[guid]::NewGuid().ToString('N').Substring(0,8)
$rawFile=Join-Path $logDir "uart_$stamp.log"
$metaFile=Join-Path $logDir "uart_$stamp.capture.json"
$manifestCopy=Join-Path $logDir "uart_$stamp.manifest.json"
Copy-Item -LiteralPath $manifestFile.FullName -Destination $manifestCopy
$record=[ordered]@{
    status='RUNNING';port=$Port;baud=115200;started=(Get-Date).ToString('o');version=$inputRecord.version
    requested_seconds=$Seconds;raw_log=$rawFile;manifest=$manifestCopy
    manifest_sha256=(Get-FileHash -LiteralPath $manifestCopy -Algorithm SHA256).Hash.ToLowerInvariant()
    board_inference_passed=$false;live_camera_passed=$false
    scope='Serial capture only; run check_c24_uart.py and retain physical board/download evidence separately'
}
$serial=New-Object System.IO.Ports.SerialPort $Port,115200,None,8,One
$serial.DtrEnable=$false
$serial.RtsEnable=$false
$serial.Handshake=[System.IO.Ports.Handshake]::None
$writer=New-Object System.IO.StreamWriter $rawFile,$false,([System.Text.UTF8Encoding]::new($false))
$writer.AutoFlush=$true
$elapsed=[System.Diagnostics.Stopwatch]::StartNew()
try {
    $serial.Open()
    Write-Host 'Capturing 115200 8N1. Start/reset the verified C24 setup now. No programming or serial commands are sent.'
    while($elapsed.Elapsed.TotalSeconds -lt $Seconds) {
        $chunk=$serial.ReadExisting()
        if($chunk){$writer.Write($chunk);Write-Host -NoNewline $chunk}
        Start-Sleep -Milliseconds 25
    }
    $record.status='CAPTURED'
} catch {
    $record.status='FAIL';$record.error=$_.Exception.Message
    throw
} finally {
    try {
        if($serial.IsOpen){$writer.Write($serial.ReadExisting());$serial.Close()}
    } finally {
        $serial.Dispose();$writer.Dispose();$elapsed.Stop()
        if($record.status -eq 'RUNNING'){$record.status='INCOMPLETE'}
        $record.finished=(Get-Date).ToString('o')
        $record.elapsed_seconds=$elapsed.Elapsed.TotalSeconds
        $record.log_sha256=(Get-FileHash -LiteralPath $rawFile -Algorithm SHA256).Hash.ToLowerInvariant()
        $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $metaFile -Encoding UTF8
    }
}
Write-Host "Saved $rawFile"
Write-Host "Use the captured manifest for validation: $manifestCopy"
