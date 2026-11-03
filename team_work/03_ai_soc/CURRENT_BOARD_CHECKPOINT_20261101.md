# 当前状态（2026-11-03更新）

2026-11-03 电脑端回归与证据核对完成：25个测试/重放入口、4项质量门ISP联合仿真通过；545个绑定文件和6个诊断包身份复核通过。真实摄像头SoT失败仍被严格拒绝，等待排线检查后实板复测。 见 [电脑端验收报告](C9_PC_ACCEPTANCE_20261103.md)。

2026-11-03 18:21 整行缓存诊断更新：最大连续pixel/source段已达到1920，但没有完整1920×1080帧。配置完成后延迟stream-on使本轮未记录CRC/ECC/帧同步错误；质量门通过32个干净周期后仍采到新的SoT错误，已严格拒绝整帧。等待完全断电后检查并重插摄像头排线，再用同一位流复测。最新C10恢复182056，六组静态推理通过；未写Flash，DDR/校准及active profile不变。 详细证据见 [整行缓存与PHY诊断](C9_RAW10_LINEBUFFER_20261103.md)。下文保留历史阶段记录。

## 最新：逐级板测完成，碎段最早已在CSI像素输出出现

两轮轻量诊断（TinyML暂不实例化，CPU/C2/DDR/视频路径保留）均校准、固件完整回读通过。最长连续有效段：CSI为18拍×4像素，RAW/ISP DE/ISP valid/联合/灰度均36拍×2像素，最终pixel与C2入口均72拍×1像素。未见RAW FIFO overflow、ISP DE/valid错位或最终fault门控置位。碎段最早已在CSI像素输出侧存在，后级保持相同72像素段；不能据此宣布摄像头硬件故障。

C2最新帧记录仍分别宽72与0，源帧/格式错误252/251、297/296，无完整帧或AI完成。窗口最大值不代表每帧情况，0/72差异尚需逐帧包/行边界观测。下一步核对valid与行边界语义，再做RAW整行缓存/连续DE接入，保持坏帧拒绝和DDR标准。

新镜像30823 XLR，setup/hold +0.319/+0.025 ns，66位Gray CDC双角通过。最后C10恢复及六组静态推理通过：`logs/c10_warm_boot_20261101/20261103_160518/attempt.json`。未写Flash，active profile仍display；没有新冷启动、真实视频或HDMI通过结论。详细结果 [C9_STAGE_TRACE_20261103.md](C9_STAGE_TRACE_20261103.md)，汇总 `logs/c9_stage_min_board_result_20261103.json`。以下为历史阶段记录。

## 最新：像素域sideband两轮板测完成，真实视频仍未通过

已引出厂家现有pixel_*接口，在原生像素域记录RUN后的RAW10 VC0 PPC集合。Pack40独立诊断配置通过P&R/STA/66位Gray CDC两角检查：60217 XLR，setup/hold +0.170/+0.026 ns。两轮校准与固件完整回读通过，PPC集合均仅4，最近pixel_wordcount均2400，未记录到图像valid在HS外。

同一位流两轮C2宽度分别0与72，源帧/格式错误244/243、238/237，完整帧与AI完成均未取得。不能据此宣布摄像头链路正常，也不能把旧全格式配置的PPC=2归为伪读；下步逐级观测RAW串并转换、ISP、灰度与C2入口的DE/valid和复位状态。现有debug时钟/复位固定零，debug=0不证明无CRC错误。

最后已恢复C10并通过六组静态推理：`logs/c10_warm_boot_20261101/20261103_130842/attempt.json`。未写Flash、未调整DDR/校准/验收标准，active profile仍为display；本轮没有物理冷启动或HDMI验收。首次缺主机BSDL的失败单列为未采得校准，不计DDR失败。详细说明 [C9_PIXEL_SIDEBAND_20261103.md](C9_PIXEL_SIDEBAND_20261103.md)，完整重放 `tools/report_c9_sideband_seed3_board.py`。

以下为按阶段保留的历史记录，旧“最新/待核实/未完成”状态由本节取代。

## 最新：包格式探针完成两轮，像素域接口仍待核实

精简版60555 XLR，setup/hold +0.061/+0.016ns，66位Gray CDC两角通过。完整版因超出78 XLR保留失败证据，未加载。两轮实板均校准/完整固件回读通过，观察wc=2400、dt=0x2B、VC=0，最近valid的PPC分别4和2；C2没有有效像素，真实视频仍未通过。

已修正主机checker实验名误报，保留原失败证据与独立v2重放，未放宽镜像/固件身份或视频标准。官方新版文档区分字节域包头状态和像素域sideband，现探针不能作为已验证跨域一致包头；下一步核对实际IP配置并改用像素域sideband/合规跨域快照，再测PPC分布与行边界。不要据当前两次PPC采样直接改像素数据流。

最新C10恢复及六组静态推理通过：`logs/c10_warm_boot_20261101/20261103_114748/attempt.json`；本轮未写Flash、未改DDR/active profile。详见 `C9_PACKET_PROBE_20261103.md`、`logs/c9_packet_board_result_20261103.json`。以下记录为先前阶段。


## 最新实板：2026-11-03 CSI 对照完成，视频未通过

三轮 DDR 校准与固件完整回读通过。新 PHY 探针两次分别记录到 C2 零有效像素、无 C2 帧记录；CSI groups 计数达到 1023 且饱和，runs=910/826。旧 geometry 镜像对照再次出现 72 像素连续 DE 段、段数超过 4095。不能把新探针的结果直接视为旧实现的真实行语义；须先排除实现/启动差异，并增加包元数据和 VS/HS 观测，再选择视频修复。

最后已恢复 C10，六组静态推理通过：`logs/c10_warm_boot_20261101/20261103_105750/attempt.json`。本轮未写 Flash、未修改 DDR 或验收标准；新镜像不推广为 active profile。详细结果 `C9_CSI_BOARD_20261103.md`，离线复核工具 `tools/report_c9_phy_board_20261103.py`。以下电脑端就绪与历史状态保留；本轮不是视频并发或物理冷启动通过。


当前板卡最后已恢复C10，六组静态TinyML通过，最新记录 `logs/c10_warm_boot_20261101/20261103_114748/attempt.json`。本轮未写Flash。

## 最新：电脑端准备已完成

用户随后要求先完成电脑端工作。本轮未打开 JTAG/串口、未重新下载板卡、未写 Flash。

CSI 探针 `build/c9_phy_geometry_image_20261102` 已完成完整构建与审计：60571 XLR，RAM224、DSP60，setup/hold +0.223/+0.026 ns，66 位 Gray CDC 两角通过；专项 RTL 和 11 项解码测试通过，镜像/固件离线身份核对通过。诊断包 `fpga_bitstreams/c9_phy_geometry_100mhz`，位流 SHA256 `da4d195aa3181ff382b043f5c32f68482352a8f187a2da89965e012880ad73b4`。未推广为 active profile。

下一步只需开始实板采集 CSI HS/valid，入口 `tools/run_c9_phy_geometry.py --capture --port COM13`；默认无 `--capture` 的命令只做本地核对。真实视频问题尚未修复；不改 DDR、校准算法、1920×1080 或坏帧验收要求。新镜像本身尚无实板校准结论。

说明 `C9_CSI_PC_READY_20261102.md`；本轮结果 `logs/c9_pc_work_20261102.json`；本地交接复制记录 `logs/c9_pc_handoff_20261102.json`。没有提交或推送 GitHub。下述暂停断点保留为历史，CSI 构建未完成的描述已被本节取代。

## 2026-11-02 晚间暂停断点

用户因额度即将耗尽要求暂停，未完成的 CSI 探针构建已停止，无后台构建继续运行。

- 新只读 geometry 镜像完成综合、P&R、STA 和 66 位 Gray CDC 双角检查：60582 XLR，setup +0.115 ns，hold +0.026 ns；未推广 active profile。
- 实板 USER2 校准通过：`logs/c9_ddr_probe_20261101/20261102_205809/attempt.json`。
- 实板小固件 3508 字节完整回读通过：`logs/ram_diagnostic_20261101/20261102_205853`。10 秒观察 252 次帧边界、251 次格式错误；最近记录最大连续 DE 段宽 72，段数超过 4095（已明确饱和），complete=0，overflow=0、AI 完成=0。只能确认行被切碎，尚不能判定 CSI/ISP 哪一级引起。
- 最后恢复 C10：`logs/c10_warm_boot_20261101/20261102_205918/attempt.json`，六组静态推理通过，未写 Flash。
- 下一探针 `build/c9_phy_geometry_image_20261102` 增加原始 CSI HS 内 payload 组数/valid 段数只读计数；RTL 仿真通过，构建在综合过程中暂停，尚无合格位流或实板结论。恢复后从 `tools/run_c9_phy_geometry.ps1` 继续完整构建，审计通过再运行 `tools/run_c9_phy_geometry.py --capture --port COM13`。
- DDR 参数、校准算法、验收标准和 1920×1080 均未改变。没有实施视频规范化修复，没有提交或推送 GitHub。本轮新增文件仍在主项目本地，尚未同步本地交接副本。

详细记录见 `C9_CAMERA_GEOMETRY_20261102.md` 和 `logs/c9_paused_checkpoint_20261102.json`。

## 前一轮通过

- C9关闭COMB4的DDR修复保持有效。显示修正版两次重新配置均校准通过。
- 定位并修正启动VS早于CDC请求通道就绪造成的虚假missed_scans；真实忙时/背压漏扫描仍计错。
- 53项C2功能回归、两个尾突发和三种启动时序通过。
- 新实现60581 XLR、RAM224、DSP60，setup/hold +0.134/+0.027ns，66位Gray CDC双角通过。
- 实板原DMA/图案视频并发检查PASS：missed_scans=0、underflow=0、AXI读写错误0，缓存正负例与所有权保护通过。
- 摄像头固件的计时采样错误已修正，原5..100ms门限保留，实板10ms进展检查通过。

## 当前C9入口

`config/c9_active_profile.json`指向display修正版。位流SHA256 `ea542809a0a884fd2d3dbc89a22cdc0d7c891e424bd1cc1179194a0934f5ee6b`，产物 `fpga_bitstreams/c9_display_fix_100mhz`。

`tools/run_ram_diagnostic.py --configure-c9`选择该配置。它暂不含C3、ROM停驻、须显式CPU装载；不是Flash自动启动最终整机。旧nopack/原失败镜像保持冻结。

## 当前阻塞

真实视频在源格式检查被拒绝。新摄像头固件20秒观察505个源帧边界、504个格式错误、0个有效推理，不能将图案并发PASS等同真实视频PASS。记录 `logs/ram_diagnostic_20261101/20261102_195114`。

下一步测量真实行宽/行数及HS、DE、pixel_valid关系，定位CSI/ISP/串并转换的格式边界。保持坏帧拒绝、DDR参数和校验条件，不盲改1920×1080常量。

完整说明 `team_work/03_ai_soc/C9_DISPLAY_FIX_20261102.md`；机器汇总 `logs/c9_display_board_20261102.json`。物理HDMI、C3传感器、融合报警、预测、网络和最终整机长稳仍需各自验收。当前C9无全容量或冷启动结论，C8全容量与C10既有Flash冷启动结论单独保留。

本轮安全文件只复制到本地交接仓库，未提交或推送GitHub。
