param(
    [Parameter(Mandatory=$true)][string]$Port,
    [ValidateRange(1,600)][int]$Seconds=120,
    [switch]$BoardPortConfirmed
)
$ErrorActionPreference='Stop'
if(-not $BoardPortConfirmed){throw 'Confirm the physical UART and pass -BoardPortConfirmed; do not select an arbitrary COM port.'}
$taskRoot=Split-Path -Parent $PSScriptRoot
$logDir=Join-Path $taskRoot 'logs\c1'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp=Get-Date -Format 'yyyyMMdd_HHmmss'
$rawFile=Join-Path $logDir "uart_$stamp.log"
$metaFile=Join-Path $logDir "uart_$stamp.capture.json"
$serial=New-Object System.IO.Ports.SerialPort $Port,115200,None,8,One
$serial.DtrEnable=$false
$serial.RtsEnable=$false
$buffer=New-Object System.Text.StringBuilder
$record=[ordered]@{port=$Port;baud=115200;started=(Get-Date).ToString('o');board_inference_passed=$false;scope='UART capture only; run check_c1_uart.py and retain board/download evidence';status='RUNNING'}
try {
    $serial.Open()
    Write-Host 'Capturing 115200 8N1. Start/reset the already verified C1 setup now. This script does not program the board.'
    $deadline=(Get-Date).AddSeconds($Seconds)
    while((Get-Date) -lt $deadline) {
        $chunk=$serial.ReadExisting()
        if($chunk){[void]$buffer.Append($chunk);Write-Host -NoNewline $chunk}
        Start-Sleep -Milliseconds 25
    }
    $record.status='CAPTURED'
} catch {
    $record.status='FAIL'
    $record.error=$_.Exception.Message
    throw
} finally {
    if($serial.IsOpen){[void]$buffer.Append($serial.ReadExisting());$serial.Close()}
    $serial.Dispose()
    [System.IO.File]::WriteAllText($rawFile,$buffer.ToString(),[System.Text.UTF8Encoding]::new($false))
    $record.finished=(Get-Date).ToString('o')
    $record.raw_log=$rawFile
    $record | ConvertTo-Json | Set-Content -LiteralPath $metaFile -Encoding UTF8
}
Write-Host "Saved $rawFile"

