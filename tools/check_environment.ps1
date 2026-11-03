[CmdletBinding()]
param(
    [string]$TDPath,
    [string]$EfinityPath,
    [string]$VivadoPath
)

# Read-only detection: no installer, executable, license file or serial port is opened.
# Optional paths may point to an installation directory, its bin folder or launcher.
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$logDirectory = Join-Path $projectRoot 'logs'
$reportPath = Join-Path $logDirectory 'environment.json'
$summaryPath = Join-Path $logDirectory 'environment_summary.txt'
$utf8 = New-Object System.Text.UTF8Encoding($true)

function Find-ToolFiles {
    param(
        [string[]]$KnownRoots,
        [string[]]$RelativeFiles,
        [string[]]$CommandNames,
        [string]$UserPath,
        [string[]]$EnvironmentNames,
        [int]$ChildDepth = 1
    )
    $roots = New-Object System.Collections.Generic.List[string]
    if ($UserPath) { $roots.Add([System.IO.Path]::GetFullPath($UserPath)) }
    foreach ($name in $EnvironmentNames) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value) { $roots.Add([Environment]::ExpandEnvironmentVariables($value.Trim('"'))) }
    }
    foreach ($root in $KnownRoots) { $roots.Add($root) }
    $found = New-Object System.Collections.Generic.List[object]
    $visited = New-Object System.Collections.Generic.HashSet[string]([StringComparer]::OrdinalIgnoreCase)
    $searched = New-Object System.Collections.Generic.List[string]
    $queue = New-Object System.Collections.Generic.Queue[object]
    foreach ($root in $roots) { $queue.Enqueue([pscustomobject]@{ Path = $root; Depth = 0 }) }
    while ($queue.Count -gt 0) {
        $entry = $queue.Dequeue()
        if (-not $visited.Add($entry.Path)) { continue }
        $searched.Add($entry.Path)
        if (-not (Test-Path -LiteralPath $entry.Path -ErrorAction SilentlyContinue)) { continue }
        $item = Get-Item -LiteralPath $entry.Path -ErrorAction SilentlyContinue
        if (-not $item) { continue }
        if (-not $item.PSIsContainer) {
            if ($CommandNames -contains $item.Name) {
                $found.Add([pscustomobject]@{ Path = $item.FullName; Source = 'supplied_path'; Root = $item.DirectoryName })
            }
            continue
        }
        foreach ($relative in $RelativeFiles) {
            $path = Join-Path $item.FullName $relative
            if (Test-Path -LiteralPath $path -PathType Leaf -ErrorAction SilentlyContinue) {
                $resolved = (Get-Item -LiteralPath $path).FullName
                $found.Add([pscustomobject]@{ Path = $resolved; Source = 'installation_directory'; Root = $item.FullName })
            }
        }
        # Inspect only immediate version/install subfolders of known vendor folders.
        # Never enumerate drives, user profile directories or unrelated documents.
        if ($entry.Depth -lt $ChildDepth) {
            foreach ($child in @(Get-ChildItem -LiteralPath $item.FullName -Directory -ErrorAction SilentlyContinue)) {
                $queue.Enqueue([pscustomobject]@{ Path = $child.FullName; Depth = $entry.Depth + 1 })
            }
        }
    }
    foreach ($name in $CommandNames) {
        foreach ($command in @(Get-Command -Name $name -CommandType Application -All -ErrorAction SilentlyContinue)) {
            if (Test-Path -LiteralPath $command.Source -PathType Leaf) {
                $found.Add([pscustomobject]@{ Path = $command.Source; Source = 'PATH'; Root = (Split-Path -Parent $command.Source) })
            }
        }
    }
    [pscustomobject]@{
        Matches = @($found | Sort-Object Path -Unique)
        SearchedRoots = @($searched)
        CommandNames = $CommandNames
    }
}

try {
    $tdDetection = Find-ToolFiles -KnownRoots @(
        'C:\Anlogic', 'D:\Anlogic', 'C:\TD', 'D:\TD',
        'C:\Program Files\Anlogic', 'C:\Program Files (x86)\Anlogic'
    ) -RelativeFiles @('bin\td.exe', 'td.exe', 'bin\td_console.exe', 'td_console.exe') `
      -CommandNames @('td.exe', 'td_console.exe') -UserPath $TDPath `
      -EnvironmentNames @('ANLOGIC_TD_PATH', 'TD_HOME')

    $efinityDetection = Find-ToolFiles -KnownRoots @(
        (Join-Path $projectRoot 'tools\efinity'),
        'C:\Efinity', 'D:\Efinity', 'C:\Efinix', 'D:\Efinix',
        'C:\Program Files\Efinix', 'C:\Program Files (x86)\Efinix'
    ) -RelativeFiles @('bin\efinity.exe', 'efinity.exe', 'bin\efx_run.py', 'scripts\efx_run.py', 'efx_run.py') `
      -CommandNames @('efinity.exe', 'efx_run.py') -UserPath $EfinityPath `
      -EnvironmentNames @('EFINITY_HOME', 'EFINITY_PATH', 'EFX_HOME') -ChildDepth 2

    $vivadoDetection = Find-ToolFiles -KnownRoots @(
        'C:\Xilinx\Vivado', 'D:\Xilinx\Vivado',
        'C:\Program Files\Xilinx\Vivado', 'C:\Program Files (x86)\Xilinx\Vivado'
    ) -RelativeFiles @('bin\xsim.bat', 'bin\xsim.exe', 'xsim.bat', 'xsim.exe', 'bin\unwrapped\win64.o\xsim.exe') `
      -CommandNames @('xsim.bat', 'xsim.exe') -UserPath $VivadoPath `
      -EnvironmentNames @('XILINX_VIVADO')

    $tdFiles = @($tdDetection.Matches)
    $efinityFiles = @($efinityDetection.Matches)
    $vivadoFiles = @($vivadoDetection.Matches)
    # The folder name is evidence of the requested release, not proof of a runnable installation.
    $xsim2018 = @($vivadoFiles | Where-Object { $_.Path -match '[\\/]2018\.3([\\/]|$)' } |
        Sort-Object @{ Expression = { if ($_.Path -match 'xsim\.bat$') { 0 } else { 1 } } }, Path)
    $tdLauncher = if ($tdFiles.Count) { $tdFiles[0].Path } else { $null }
    $efinityLauncher = if ($efinityFiles.Count) { $efinityFiles[0].Path } else { $null }
    $xsimLauncher = if ($xsim2018.Count) { $xsim2018[0].Path } else { $null }

    $serialNames = @()
    $serialReadStatus = 'read_only_success'
    $serialReadError = $null
    try { $serialNames = @([System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object) }
    catch { $serialReadStatus = 'unavailable'; $serialReadError = $_.Exception.Message }

    $timeZone = [TimeZoneInfo]::FindSystemTimeZoneById('China Standard Time')
    $chinaTime = [TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow, $timeZone)
    $report = [ordered]@{
        schema_version = 1
        checked_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        checked_at_asia_shanghai = $chinaTime.ToString('yyyy-MM-dd HH:mm:ss zzz')
        project_root = $projectRoot
        detection_mode = 'read_only_file_presence_and_serial_port_names'
        powershell_version = $PSVersionTable.PSVersion.ToString()
        competition = [ordered]@{
            track = '易灵思赛道'
            topic = '多模态 AI 智能终端'
            platform = '基于易灵思 FPGA 芯片的自制开发板'
            track_status = 'confirmed_by_user_registration_screenshot'
            user_selected = '赛题三、平台三'
        }
        hardware = [ordered]@{
            user_reported_chip_model = 'Ti60F225'
            chip_model_source = 'user_provided'
            board_manufacturer = '待确认'
            board_revision = '待确认'
            camera_model = '待确认'
            connection_status = '用户表示已有设备，尚未连接；本脚本未核实或连接硬件'
            serial_port_names = $serialNames
            serial_detection_status = $serialReadStatus
            serial_detection_error = $serialReadError
            serial_note = '仅列出串口名称，未打开端口；串口存在不能证明 FPGA 已连接。'
        }
        tools = [ordered]@{
            td = [ordered]@{
                status = $(if ($tdFiles.Count) { 'files_found_not_run' } else { 'not_found' })
                path = $tdLauncher
                matches = $tdFiles
                searched_roots = @($tdDetection.SearchedRoots)
                path_commands_checked = @($tdDetection.CommandNames)
                supports_user_chip = $false
                note = '安路 TD 不支持易灵思 Ti60，不能用于本板卡的综合、布局布线或生成下载文件。'
            }
            efinity = [ordered]@{
                status = $(if ($efinityFiles.Count) { 'files_found_not_run' } else { 'not_found' })
                path = $efinityLauncher
                matches = $efinityFiles
                searched_roots = @($efinityDetection.SearchedRoots)
                path_commands_checked = @($efinityDetection.CommandNames)
                installation_verified = $false
                license_status = 'not_checked'
                note = $(if ($efinityFiles.Count) { '找到 Efinity 文件候选；未启动，版本、器件支持和许可仍需实际验证。' } else { '未在常见路径、PATH 或指定路径找到 Efinity；若已安装在其他位置，请使用 -EfinityPath 指定。' })
            }
            vivado2018_3 = [ordered]@{
                status = $(if ($xsim2018.Count) { 'files_found_not_run' } elseif ($vivadoFiles.Count) { 'xsim_found_release_unconfirmed' } else { 'not_found' })
                required_release = '2018.3'
                version_evidence = $(if ($xsim2018.Count) { '2018.3 in installation folder path' } else { 'none' })
                xsim_path = $xsimLauncher
                matches = $vivadoFiles
                searched_roots = @($vivadoDetection.SearchedRoots)
                path_commands_checked = @($vivadoDetection.CommandNames)
                generic_rtl_simulation_verified = $false
                supports_user_chip_bitstream = $false
                note = 'XSim 可用于通用 RTL 仿真；本检测只确认文件存在，未运行仿真。Vivado 不能生成 Ti60 下载文件。'
            }
        }
        readiness = [ordered]@{
            board_build_ready = $false
            board_programming_ready = $false
            hardware_debug_complete = $false
            blockers = @(
                $(if (-not $efinityFiles.Count) { '未检测到 Efinity' } else { 'Efinity 版本、器件支持和许可尚未验证' }),
                '缺少具体板卡厂商、版本、原理图与官方引脚约束确认',
                '摄像头型号与接口待确认',
                '设备未连接，尚未执行板级下载与实际调试'
            )
        }
        safeguards = @(
            '未安装或下载软件',
            '未启动 FPGA 软件或执行下载',
            '未打开串口或连接板卡',
            '未读取许可文件或许可内容',
            '仅检测指定路径、工具环境变量、PATH 和固定厂家目录',
            '仅在本项目 logs 目录写入检测报告'
        )
    }
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
    $json = $report | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($reportPath, $json, $utf8)
    $lines = @(
        'FPGA 参赛项目环境检测（只读）',
        ('检测时间（北京时间）：' + $report.checked_at_asia_shanghai),
        '已确认：易灵思赛道 / 多模态 AI 智能终端 / 自制开发板',
        '用户提供芯片：Ti60F225；具体板卡版本及摄像头仍待确认。',
        ('安路 TD：' + $(if ($tdLauncher) { $tdLauncher } else { '未检测到' })),
        '注意：安路 TD 不支持 Ti60，本项目板级构建需要易灵思 Efinity。',
        ('Efinity：' + $(if ($efinityLauncher) { $efinityLauncher + '（只确认文件存在）' } else { '未检测到' })),
        ('Vivado 2018.3 XSim：' + $(if ($xsimLauncher) { $xsimLauncher + '（只确认文件存在）' } else { '未检测到可确认版本的 XSim' })),
        ('串口名称（未打开）：' + $(if ($serialNames.Count) { $serialNames -join ', ' } else { '无 / 不可读取' })),
        '独立工程编译结果：请查看 logs/efinity_*_compile.json；本检测只确认软件路径。',
        '实体板下载与运行结果：尚未验证。',
        '本次未运行软件、未读取许可文件、未安装软件、未连接板卡。',
        ('完整报告：' + $reportPath)
    )
    [System.IO.File]::WriteAllText($summaryPath, ($lines -join [Environment]::NewLine) + [Environment]::NewLine, $utf8)
    foreach ($line in $lines) { Write-Host $line }
    exit 0
}
catch {
    Write-Error ('Environment check failed: ' + $_.Exception.Message) -ErrorAction Continue
    exit 1
}
