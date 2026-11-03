# 暂停检查点：C7 冷启动与 C9 DMA/真实视频（2026-11-01）

用户因额度不足要求先停。暂停新增构建、下载和板上测试；已于 14:44:56（UTC+08:00）完成 Flash 独立全片回读，SHA256 与预期一致；所有擦写/回读操作已结束。不要自动继续下一轮。

已完成：
- 原 C7 CPU/DDR/静态 TinyML 实板证据仍有效，见 C7_BOARD_ACCEPTANCE_20261101.md；原 C7 工程和 C24 固件保持原样。
- 当前仅接摄像头，未接 HDMI 显示器；不能宣布 HDMI 实际画面通过。
- 实读 Flash EF6017（Winbond W25Q64，8MiB）。两次独立全片备份 SHA256 完全相同：3bd34df462240bbf1057553c07943ff8cf95e820268def68c5242b45b71ba67b。
- 私有备份目录：C:/Users/16034/Downloads/FPGA/FPGA_2026_T3_P3/build/private_flash_backup_20261101/20261101_141853/。不得把未知旧 Flash 原始内容上传 GitHub。
- 已将经过实板验证的原 C7（bit SHA dd49ca7f8064a70e52ff1370646e6858c20d6d659249b8b00c126f95e7d33411）和原 C1 固件写入 Flash，其他区域从原备份保留。新 8MiB 原始镜像 SHA256：2b83d24388a887aae9e20638e50352fd2bc4c20dcccb320e001731429148d04d。
- 厂家程序首次按默认等待时间写入后校验失败，程序自身改用最大等待时间重写后，整片主机校验成功。不是两次都成功，原始日志须保留。
- 当前已结束擦写，正在/已经完成独立第二次全片只读回读，最终状态必须读取 logs/c7_cold_flash_program_20261101.json。PASS_FLASH_WRITE_AND_TWO_FULL_VERIFICATIONS_COLD_BOOT_PENDING 才表示完整独立 SHA256 已一致。
- 当前 FPGA SRAM 运行的是官方 Ti60 JTAG-to-SPI bridge，CPU/视频未运行。官方桥文件 tools/efinity/2026.1/pgm/fli/titanium/u10660A79.bit（SHA256 2fa6bda7ad79e03edc2f862c02e956823a90b4667b23229e2b2bc692bb63927e）。断电后预计从新 Flash 加载原 C7+C1，但尚未实际验收。

下次最先做：
1. 读取 Flash 最终 JSON，核对 expected_flash_sha256 与 readback_sha256 相同且操作已结束。
2. 先打开 COM13（115200/8N1/DTR=RTS=false）并准备掉线重连捕获，再请用户断开所有供电（含USB）、等待灯熄灭并插回原电脑 USB 口。只采集，不重新 JTAG 配置/加载CPU，验证 Flash 自动启动的 C1 BOOT、六图推理、DONE 与桌面对照；这是尚未完成的 C7 冷启动验收。
3. 原 USB(1) B/MI_01 为 libusbK，C/MI_02=COM13。换 USB 口可能重新变为 FTDI/COM16，需返回原口，不能猜通道。

C9 在做的内容（全部尚无实板通过证据）：
- 隔离工程 projects/09_c7_live_acceptance，从已验收的 C7 克隆；固定 C2 map=1（保留视频/AI地址已在256MiB范围内，软件启动前仍须验地址别名），C3 IO=0，像素源 RUN 默认0，源类型只能在运行前提交一次，直到共同复位/重新配置才可切换。
- team_work/03_ai_soc/c9_live/rtl：一次一帧、可选灰度值的硬件图案源，用于真实 C2 AXI DMA stale-cache 负例/失效后正例；不冒充真实摄像头。图案包含关闭VS；后续帧不重复开头VS，已通过实际 A capture 的两帧/10368采样检查。
- 五个域的监测快照，原版整组宽快照首次 P&R 打包为61295 XLR，超过60800，未生成/下载该版本。
- 已改为每组一次捕获一个64-bit原子数据对：CPU按pair_select(0..3)遍历，保留所有32-bit字段、不截断计数；不同数据对属于不同采集时刻，必须用采集窗口标注，不能声称整组同时快照。
- 该压缩版已通过31项APB/CDC/冻结/停钟/复位检查及实际A图案采样检查，但尚未重新准备工程、综合或P&R。当前 LIVE_MANIFEST/source_sha 仍对应压缩前版本，必须先运行 tools/prepare_c7_live.py。
- 新 APB页 E0xx ID 已改为0x43394c32；SNAP命令写 E010=(pair<<8)|1，等待状态bit1，分别从E040/44、E060/64、E080/84、E0A0/A4、E0C0/C4读取五组64-bit数据，写E014=1释放，然后下一pair。不可继续读每组旧的8个连续寄存器。
- 固件原型 team_work/03_ai_soc/c9_live/firmware/dma_main.c 与 firmware/c9_dma_diag/ 已构建，但仍检查旧ID 0x43394c31、使用旧宽快照读取。下次必须先改ID与snapshot()为4轮pair采集，再重建；本原型没有上板。
- DMA原型计划：验证高DDR地址互不别名；图案3c填充slot0并预热cacheline；释放后C2 DMA以c3重写同槽；省略invalidate必须观察旧3c，invalidate后必须为c3且整图FNV一致；持有slot0并让下一帧写slot1，旧generation释放须拒绝，验证READING不被覆盖。
- DMA和真实视频的实板加载/日志严格校验工具、实时TinyML固件、C9物理审计仍待完成。不能直接复用原C7加载脚本的工程/审计绑定来加载C9。

复现工具：tools/prepare_c7_live.py、test_c7_live_rtl.py、generate_soc_live_cdc.py、run_soc_live.ps1、build_c9_dma.py。恢复顺序为修固件快照API→RTL回归→prepare→interface/map/pnr/sta_tclsh/pgm→独立C9审计→临时JTAG DMA验收→重配相机源的真实视频/推理并发验收。

C7 Flash相关代码位于 build/c7_live_20261101/flash_backup.py、prepare_c7_cold_image.py、program_c7_cold_flash.py，均为本次私有工作脚本。不要重复执行program脚本来代替冷启动；Flash已经写入，先看JSON。未提交或推送本轮更改到GitHub。