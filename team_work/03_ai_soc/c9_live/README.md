# C9 视频、DMA 与 TinyML 实板诊断

2026-11-03 电脑端回归与证据核对完成：25个测试/重放入口、4项质量门ISP联合仿真通过；545个绑定文件和6个诊断包身份复核通过。真实摄像头SoT失败仍被严格拒绝，等待排线检查后实板复测。 见 [电脑端验收报告](../C9_PC_ACCEPTANCE_20261103.md)。

2026-11-03 18:21 整行缓存诊断更新：最大连续pixel/source段已达到1920，但没有完整1920×1080帧。配置完成后延迟stream-on使本轮未记录CRC/ECC/帧同步错误；质量门通过32个干净周期后仍采到新的SoT错误，已严格拒绝整帧。等待完全断电后检查并重插摄像头排线，再用同一位流复测。最新C10恢复182056，六组静态推理通过；未写Flash，DDR/校准及active profile不变。 详细证据见 [整行缓存与PHY诊断](../C9_RAW10_LINEBUFFER_20261103.md)。下文保留历史阶段记录。

2026-11-03 最新分级实板：两轮均测到CSI 18×4PPC → RAW/ISP/灰度36×2PPC → C2入口72×1PPC，首个碎段已在CSI像素输出出现。没有完整帧；C2最后记录0/72的逐帧差异仍待解释。轻量诊断未含TinyML，C10六组静态推理已恢复、未写Flash；下一步核对包/行边界并设计整行缓存。见 [分级检查](../C9_STAGE_TRACE_20261103.md)。以下为历史阶段记录。

2026-11-03 最新像素域sideband：Pack40/seed3诊断P&R和两轮板测完成，DDR校准/固件回读通过，RUN后RAW10 VC0的PPC集合仅4、最近WC2400；C2宽度仍0/72、完整帧与AI均未取得。C10六组静态推理已恢复，未写Flash；下步逐级核对RAW/ISP/灰度/C2的DE、valid与复位。见 [像素域诊断结果](../C9_PIXEL_SIDEBAND_20261103.md)。以下为历史阶段记录。

2026-11-03 包格式观测更新：两轮校准/固件回读通过，PPC最后valid采样分别4/2，视频仍未通过。须核对像素域sideband/包头CDC并统计分布后再修像素路径，C10已恢复、未写Flash。见 [包格式诊断](../C9_PACKET_PROBE_20261103.md)。


2026-11-03 实板对照：三轮 DDR 校准通过，真实视频仍失败；新 PHY 探针与旧 geometry 视频表现不同，暂不可据饱和计数确定修复方案。C10 六组静态推理已恢复，未写 Flash。见 [CSI 实板结果](../C9_CSI_BOARD_20261103.md)。
2026-11-02 最新电脑端：CSI HS/valid 只读探针已完成综合、P&R、STA 与 66 位 Gray CDC 两角审计（setup +0.223 ns，hold +0.026 ns），11 项解码测试通过，诊断包已就绪。当前阶段未访问板卡，真实视频仍等待下一次采集；说明 [C9_CSI_PC_READY_20261102.md](../C9_CSI_PC_READY_20261102.md)。

2026-11-02 晚间：已实板确认 C2 连续 DE 段最大仅 72 像素，段数超过 4095，真实视频仍未通过；C10 已恢复、六组静态推理通过。用户因额度要求暂停，后续 CSI 只读探针构建已停止。见 [C9_CAMERA_GEOMETRY_20261102.md](../C9_CAMERA_GEOMETRY_20261102.md)。

2026-11-02 最新：默认`run_ram_diagnostic.py --configure-c9`选择`config/c9_active_profile.json`的display修正版，已通过实板原DMA/图案视频并发检查。真实摄像头尝试应使用独立`firmware/c9_camera_timefix/BUILD_RECORD.json`和`tinyml_c9_timefix.bin`，它修正快照日志导致的计时采样错误；原固件保留复现。真实源仍有505个边界/504个格式错误、0个有效推理，尚未通过。完整状态见上级 `C9_DISPLAY_FIX_20261102.md`。

这是隔离验收工程 `projects/09_c7_live_acceptance`，不是新的整机发布镜像。保留唯一 DDR 控制器、CPU、C2 帧缓存和摄像头/显示通路；为给诊断计数器留下布线空间，C3 传感器 APB 后端暂不实例化，访问返回错误，I²C/GPIO 与蜂鸣器不动作。完整 C7 和 C24 不改动。

目前固件与 RTL 仿真已通过，P&R 和实板结果需以独立日志为准，不能由编译成功推定硬件通过。

## 专用 APB 页面

基地址为厂家 `IO_APB_SLAVE_0_INPUT + 0xE000`，ID `0x43394C34`。

| 偏移 | 定义 |
|---|---|
| 00 | ID，只读 |
| 04 | 状态 bit0 RUN、bit1 PATTERN、bit2 固定映射；写 `C9A70001` 提交摄像头，`C9A70003` 提交测试图 |
| 08 | 测试图命令 ready；写灰度值触发一帧 |
| 10 | 写 `(pair << 8) | 1` 请求快照，pair=0..3；读 bit0 busy、bit1 ready |
| 14 | 读快照序号；写 1 释放所有域的这一对数据 |
| 40/44 | DDR 域 64 位快照 |
| 60/64 | 视频域 64 位快照 |
| 80/84 | 显示域 64 位快照 |
| A0/A4 | 摄像头 I²C 域 64 位快照 |
| C0/C4 | MIPI 域 64 位快照 |

C2 地址映射从公共复位开始固定开启，像素源 RUN 默认关闭。固件必须先验证 6 个 DDR 地址互不别名以及共享时间前进，再提交源。源选择只能提交一次，切换测试图与摄像头必须重新配置或公共复位。

每次请求在五个原生时钟域各锁存同一 pair 的两个 32 位字，数据保持到 ACK。不同域、不同 pair 并不在同一时刻采集，因此日志保留快照起止时间；不可把跨 pair 的组合称为全组原子快照。停止任一源时钟应保持 busy，不能以旧值伪报完成。

四对字顺序如下：

- DDR：published、dropped、write_errors、read_errors、repeated、empty_scans、max_aw_wait、max_ar_wait。
- 视频：capture_source_frames、capture_format_errors、overflow_frames、a_completed、a_rejected、a_source_faults、pattern_completed、source_flags。
- 显示：frame_id、timestamp_ms、completed_scans、underflows、missed_scans、flags。末两字为 0。
- 摄像头：原生寄存器读回 128 位、valid，后续为 0。
- MIPI：debug_out、camera_fault，后续为 0。

source_flags bit0 fault、bit1 pattern_busy、bit2 pattern_mode、bit3 RUN。显示 flags bit0 busy、bit1 available、bit2 failed。

## 两类固件

- `tools/build_c9_dma.py`：三个灰度测试帧，验证真实 C2 AXI 搬运、缓存旧数据负例/失效后新数据、全图 FNV、过期 generation 拒绝和租用槽保护。测试图不构成真实摄像头验收。
- `tools/build_c9_tinyml.py`：独立 `tinyml_c9`，运行合成模型自检后接入摄像头，限制采集 12 帧，记录来源、统一时间、原图/张量 FNV 和原始 INT8 输出。运行时地址与时间检查是打开源的必要条件。

`tools/run_ram_diagnostic.py` 只做 SRAM 配置和 DDR 固件装载，不写 Flash；先核对审计和源码 SHA，再完整回读二进制，匹配后才执行。`tools/check_c9_uart.py` 区分 `dma` 和 `camera` 两种证据。

未接显示器时，可验证内部显示读出并发和计数，但不能验收 HDMI 接线、显示器兼容性和实际画面。
