$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$build=Join-Path $root 'build\led_selftest'
$log=Join-Path $root 'logs\tb_key_detect.run.log'
New-Item -ItemType Directory -Force -Path $build | Out-Null
$image=Join-Path $build 'key.vvp'
& (Join-Path $root 'tools\iverilog\bin\iverilog.exe') -g2012 -s tb_key_detect -o $image (Join-Path $root 'projects\01_led\src\key_detect.v') (Join-Path $root 'sim\tb_key_detect.sv')
if($LASTEXITCODE -ne 0){throw 'Key test compilation failed.'}
$text=& (Join-Path $root 'tools\iverilog\bin\vvp.exe') $image 2>&1 | Out-String
$code=$LASTEXITCODE
$text | Set-Content -LiteralPath $log -Encoding UTF8
if($code -ne 0 -or $text -notmatch 'PASS tb_key_detect' -or $text -match 'FATAL|FAIL'){throw "Key debounce test failed; see $log"}
Write-Host $text
