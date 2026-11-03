function Get-TaskFileSha256 {
    param([Parameter(Mandatory=$true)][string]$Path)
    $stream=[System.IO.File]::OpenRead($Path)
    $algorithm=[System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes=$algorithm.ComputeHash($stream)
        return ([System.BitConverter]::ToString($bytes)).Replace('-','')
    } finally {
        $algorithm.Dispose()
        $stream.Dispose()
    }
}
