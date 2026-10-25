param([ValidateRange(1,8)][int]$Jobs=2)
$ErrorActionPreference='Stop'
& python (Join-Path $PSScriptRoot 'build_c24.py') --jobs $Jobs
exit $LASTEXITCODE
