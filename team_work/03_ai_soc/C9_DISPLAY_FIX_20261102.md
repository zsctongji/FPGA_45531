# C9 启动显示漏扫描定位与修正

## 已定位原因

原C9实板日志 `logs/ram_diagnostic_20261101/20261102_183914` 中，显示missed_scans在before快照已为1，after仍为1；underflow为0。原严格并发检查因此失败，不能用测试期间未增长替代零错误标准。

启动小复现直接实例化实际 `c2_video_scanout` 与实际 `c2_cdc_mailbox` 请求通道。共同复位释放后，mailbox要等待显示域两级释放寄存器就绪；如果VS已经为高，或此时出现上升沿，旧scanout把这个尚未具备请求服务能力的启动边界计为missed。

`tools/test_c9_scanout_startup.py --baseline` 可重现：START_MODE=0/1均报startup false missed_scans=1并退出1；START_MODE=2（首次ready时的合法VS）通过。它与实板中运行前已出现1次计数的现象一致；修正版实板已复测通过，见下方结果。

## 修正边界

候选源码：`c9_live/display_fix/c2_video_scanout.sv`。只增加一次性的请求通道初始化标志；首次ready前不把复位期VS当作运行期扫描请求，首次ready当拍的合法上升沿仍能请求扫描。初始化后，busy、已有请求或mailbox背压导致的真实漏扫描仍累加并置失败/排空状态。

没有清零运行中计数、扣掉首个错误或修改UART验收条件。DDR参数、校准流程、COMB4=0以及原时钟/引脚/电压约束均保持不变。旧共享模块及已验收C8/C10/C9位流不覆盖。

## 验证入口与当前进度

- `python -X utf8 tools/test_c9_scanout_startup.py`：三种启动时序通过；还验证真实busy及持续mailbox背压时必须计错，以及排空后的恢复。
- `python -X utf8 tools/test_c9_display_c2.py`：在独立目录复用53项C2功能回归和1/6拍尾突发测试；53项及两个尾突发检查全部通过，包含1080p并发与故障恢复用例。
- `tools/prepare_c9_display_fix.py`、`tools/run_c9_display_fix.ps1`、`tools/audit_c9_display_fix.py`：独立工程 `build/c9_display_fix_20261102`。首次副本漏带rtl/vendor_a目录的失败日志保存在source_copy_rejected，补齐后重新执行；该失败没有生成或下载有效镜像。
- 实现和实板均已完成：60581/60800 XLR、224 RAM、60 DSP；setup/hold +0.134/+0.027 ns，66位Gray CDC双角通过。当前默认C9入口为修正版display配置；旧nopack版本保留。

审计要求：只替换scanout；其他编译RTL、外设配置和约束与父版相同；53项回归及尾突发通过；新实现的引脚、主setup/hold和66位Gray CDC双角通过，且所有编程产物为本次新生成。任何条件失败都不把候选下载到板卡。

## 后续实板顺序

实现审计通过后，先采集USER2核对DDR校准，再运行原C9 DMA固件及未修改的 `tools/check_c9_uart.py --mode dma`，检查完整并发结果。图案源与真实摄像头证据继续区分；没有HDMI显示器时不宣称物理画面通过。测试后恢复C10并核对六组TinyML，本轮不写Flash。

## 实板结果与当前版本

- 位流SHA256：`ea542809a0a884fd2d3dbc89a22cdc0d7c891e424bd1cc1179194a0934f5ee6b`。
- DDR两次重新配置校准通过：`logs/c9_ddr_probe_20261101/20261102_192944`、`20261102_193339`。
- 原DMA固件及原通过条件实板PASS：`logs/ram_diagnostic_20261101/20261102_193055`。missed_scans测试前/后均0，underflow=0，AXI读写错误0；缓存正负例、整图校验和所有权保护通过。
- 机器汇总：`logs/c9_display_board_20261102.json`；产物：`fpga_bitstreams/c9_display_fix_100mhz`；固定配置：`config/c9_display_profile_20261102.json`，当前别名`config/c9_active_profile.json`。
- `run_ram_diagnostic.py --configure-c9`已选择修正版。仍是ROM停驻、需显式CPU装载、不含C3的诊断镜像，不是Flash自动启动整机。

## 真实摄像头尝试与未完成项

旧摄像头固件在`20261102_193610`完整写入/读回后，合成模型自检通过，但在开启真实源前报time_progress。原因是计时起点在大量UART快照输出前采样，日志耗时被错误算入10ms等待。新独立源码`c9_live/camera_time_fix/tinyml_main.cc`只在快照打印后重新采样，仍执行5..100ms原门限；冻结时间、读取失败及错误时钟速率仍被拒绝。

`tools/build_c9_camera_timefix.py`先将旧对象重新链接，所得BIN逐字节匹配原合格固件，然后只重新编译main单元及新构建ID。原固件/源码不覆盖；新的`firmware/c9_camera_timefix`版本为`c9time-0beb9d9f3f36baa1`。原链接响应文件的Windows路径转义错误及一次编译器子进程启动失败保留于build.log；原命令仅对明确CreateProcess启动失败重试，不忽略语法错误。

新固件实板记录`logs/ram_diagnostic_20261101/20261102_195114`：完整1395904字节回读一致，时间检查为211783→211793ms，通过后提交真实源。约20秒观察505个源帧边界、504个格式错误、overflow=0、copied=0、accepted=0；不能推断余下1个边界为完整帧。**真实摄像头推理验收仍失败，未取得有效图像或桌面参考比对。**

额外修正了主机工具对厂家MicroPrintf十六进制`0x`前缀的解析兼容，以及私有缓冲地址的同类解析；没有放宽任何计数、时效或有效帧条件。原实际DMA PASS、原实际漏扫描FAIL及畸形数值拒绝均保留。当前坏摄像头记录在新解析器中仍为FAIL。输入图像没有上传；本次没有成功导出真实图像缓冲。

三种理想时钟相位下的实际ISP/串并转换小帧仿真通过，范围为32×8合成连续有效像素；它不模拟真实MIPI突发和电气行为。下一步需要取得真实输入的行宽、行数、HS/DE与pixel_valid关系，区分CSI输出、ISP和串并转换在哪一段破坏格式，再实现必要的流规范化。不能仅修改期待宽高或接受坏帧来过验收。

最后恢复C10及六组TinyML通过：`logs/c10_warm_boot_20261101/20261102_195756`。本轮未写Flash。源码、固件、位流及选定证据只同步本地交接仓库，未提交/推送GitHub。真实摄像头、物理HDMI画面、C3联合和完整整机验收分别保留为待办。
