# C：RISC-V/TinyML、统一工程、融合与预测

2026-11-03 电脑端回归与证据核对完成：25个测试/重放入口、4项质量门ISP联合仿真通过；545个绑定文件和6个诊断包身份复核通过。真实摄像头SoT失败仍被严格拒绝，等待排线检查后实板复测。 见 [电脑端验收报告](C9_PC_ACCEPTANCE_20261103.md)。

2026-11-03 18:21 整行缓存诊断更新：最大连续pixel/source段已达到1920，但没有完整1920×1080帧。配置完成后延迟stream-on使本轮未记录CRC/ECC/帧同步错误；质量门通过32个干净周期后仍采到新的SoT错误，已严格拒绝整帧。等待完全断电后检查并重插摄像头排线，再用同一位流复测。最新C10恢复182056，六组静态推理通过；未写Flash，DDR/校准及active profile不变。 详细证据见 [整行缓存与PHY诊断](C9_RAW10_LINEBUFFER_20261103.md)。下文保留历史阶段记录。

2026-11-03 最新分级实板：两轮均测到CSI 18×4PPC → RAW/ISP/灰度36×2PPC → C2入口72×1PPC，首个碎段已在CSI像素输出出现。没有完整帧；C2最后记录0/72的逐帧差异仍待解释。轻量诊断未含TinyML，C10六组静态推理已恢复、未写Flash；下一步核对包/行边界并设计整行缓存。见 [分级检查](C9_STAGE_TRACE_20261103.md)。以下为历史阶段记录。

2026-11-03 最新像素域sideband：Pack40/seed3诊断P&R和两轮板测完成，DDR校准/固件回读通过，RUN后RAW10 VC0的PPC集合仅4、最近WC2400；C2宽度仍0/72、完整帧与AI均未取得。C10六组静态推理已恢复，未写Flash；下步逐级核对RAW/ISP/灰度/C2的DE、valid与复位。见 [像素域诊断结果](C9_PIXEL_SIDEBAND_20261103.md)。以下为历史阶段记录。

2026-11-03 包格式观测更新：两轮校准/固件回读通过，PPC最后valid采样分别4/2，视频仍未通过。须核对像素域sideband/包头CDC并统计分布后再修像素路径，C10已恢复、未写Flash。见 [包格式诊断](C9_PACKET_PROBE_20261103.md)。


2026-11-03 实板对照：三轮 DDR 校准通过，真实视频仍失败；新 PHY 探针与旧 geometry 视频表现不同，暂不可据饱和计数确定修复方案。C10 六组静态推理已恢复，未写 Flash。见 [CSI 实板结果](C9_CSI_BOARD_20261103.md)。
2026-11-02 最新电脑端：CSI HS/valid 只读探针已完成综合、P&R、STA 与 66 位 Gray CDC 两角审计（setup +0.223 ns，hold +0.026 ns），11 项解码测试通过，诊断包已就绪。当前阶段未访问板卡，真实视频仍等待下一次采集；说明 [C9_CSI_PC_READY_20261102.md](C9_CSI_PC_READY_20261102.md)。

2026-11-02 晚间：已实板确认 C2 连续 DE 段最大仅 72 像素，段数超过 4095，真实视频仍未通过；C10 已恢复、六组静态推理通过。用户因额度要求暂停，后续 CSI 只读探针构建已停止。见 [C9_CAMERA_GEOMETRY_20261102.md](C9_CAMERA_GEOMETRY_20261102.md)。

2026-11-02 后续：显示启动误计数已修正，实板原DMA/图案视频并发验收PASS，missed/underflow/AXI错误均0；默认C9入口已切到display修正版。真实摄像头固件的计时采样问题已修正，但真实源505个边界中504帧格式错误，尚无有效推理；下一步核对源行宽/行数及DE/valid。见 [C9_DISPLAY_FIX_20261102.md](C9_DISPLAY_FIX_20261102.md)。板卡最后恢复C10，未写Flash。下方为历史阶段记录。

2026-11-02 最新：C9 DDR校准阻塞在关闭COMB4打包的诊断配置下解除；两次重新配置校准通过，实际CPU程序完整读回及DDR/DMA数据步骤执行通过。完整并发仍因显示missed_scans=1未通过，DDR参数及校验标准不变。默认`run_ram_diagnostic.py --configure-c9`已指向该配置；当前板卡恢复C10，未写Flash。见 [DDR_FIX_BOARD_RESULT_20261102.md](DDR_FIX_BOARD_RESULT_20261102.md) 和 [CURRENT_BOARD_CHECKPOINT_20261101.md](CURRENT_BOARD_CHECKPOINT_20261101.md)。以下为各阶段历史记录。

2026-11-01 C7 CPU/DDR/静态 TinyML 实板通过：定位并修正 CPU 厂家桥与通用适配器的单拍地址规则不匹配；28 store / 48 read 回归通过后重新综合/P&R，setup +0.270 ns、hold +0.023 ns、XLR 58,926/60,800。实板 CPU 的 1 MiB 四图案、缓存 invalidate/refill、byte/halfword 通道和公共时间通过；原 C1 六次推理的 INT8 分数与桌面参考逐项相同，Invoke 约 250 ms（含现有日志）。仅 JTAG SRAM/DDR 加载，未写 Flash；外部 DMA stale-cache 负例、真实视频/传感器并发及 C7 冷上电/Flash 自动启动仍待验收。见 [C7_BOARD_ACCEPTANCE_20261101.md](C7_BOARD_ACCEPTANCE_20261101.md)。

2026-11-01 当前 DDR 实板状态：首次 JTAG 加载、KEY0 复位，以及用户确认重新上电后再次 JTAG 配置三次均通过；每次核对 67,108,889 个 word，均有两条完整 PASS、E=00。重新上电测试为 23 条 UART 记录，断电过程由用户确认，未写 Flash。独立诊断已形成三次证据，C7 CPU/AI/视频整机和 Flash 自动启动仍待验收。见 [DDR_BOARD_RESULT_20261101.md](DDR_BOARD_RESULT_20261101.md)；以下各条保留对应阶段的历史状态。

2026-11-01 KEY0 实板复测通过：串口实际捕获复位清零、重新校准后的测试过程和两条完整容量 PASS；26 条记录、N=04000019、E=00。与首次 JTAG 测试分开保存证据，未重新配置 FPGA、未写 Flash。冷上电后重新配置及整机验收仍待完成。见 [DDR_BOARD_RESULT_20261101.md](DDR_BOARD_RESULT_20261101.md)。

2026-11-01 独立 DDR 首次实板通过：FT4232HL 的 B/MI_01 使用 libusbK，C/MI_02 保留 UART COM13。以 1 MHz JTAG 临时加载固定 SHA256 的 C8 镜像，实际收到 23 条 UART 记录，其中两条完整容量 PASS；256 MiB 地址别名与四轮全容量读写核对 67,108,889 个 word，L=3、C=1、E=00。未写 Flash，KEY0 重测、冷上电后重新配置及 C7 整机验收仍待完成。见 [DDR_BOARD_RESULT_20261101.md](DDR_BOARD_RESULT_20261101.md)。以下条目保留各日期的历史状态。

2026-10-31 独立 DDR 诊断：新增 `projects/08_ddr_diag` 和 `28_build_ddr_diag.cmd`。已生成 JTAG 临时加载镜像，具备独立 LED/UART 状态、PLL/校准超时、地址别名探测及四图案 256 MiB 读写。12 项 AXI、4 组 UART 和 8 项解析器检查通过；P&R setup +0.324 ns、hold +0.027 ns。该镜像会破坏 DDR 内容，尚无上板执行证据。见 [DDR_DIAGNOSTIC_RUNBOOK.md](DDR_DIAGNOSTIC_RUNBOOK.md)。

2026-10-31 电压反馈与 DDR 修正：用户报告电压符合预期；C7 tFAW 改为 50 ns 后重新综合/P&R/STA，setup +0.119 ns、hold +0.026 ns，XLR 58,702/60,800。新增 27_prepare_board_review.cmd，46 项静态检查及配置/CPU 区间检查通过，仍待 DDR 校准、读写和冷启动。见 [BOARD_PREFLIGHT_20261031.md](BOARD_PREFLIGHT_20261031.md)。

2026-10-31 整机物理实现（修正前历史）：新增 `projects/07_soc_physical`，见 [PHYSICAL_V4_20261031.md](PHYSICAL_V4_20261031.md)，复现入口 `26_build_soc_physical.cmd`。V4 参考引脚/电压/PLL 已统一，100 MHz CPU 整机完成 P&R；setup +0.127 ns、hold +0.026 ns，66 位 Gray CDC 两角检查通过。实际占用 58,887/60,800 XLR；58 项 RTL 与 543 项物理参考审计通过。未确认实际 PCB/供电/Flash，物理发布仍禁用；下文关于 C6 尚未 P&R 的描述保留为历史记录。

2026-10-31 BRAM 优化与引脚审计：见 [BRAM_OPTIMIZATION_20261031.md](BRAM_OPTIMIZATION_20261031.md) 和 [PIN_OWNERSHIP_20261031.md](PIN_OWNERSHIP_20261031.md)。native map 为 39,656 LUT4 / 36,902 FF / 174 RAM10；53 次 RTL 与 781 项包检查 PASS。25_audit_bram_pins.cmd 复核综合证据与管脚所有权，物理约束仍为 REVIEW_REQUIRED。下文 49/50 次与旧资源数字是历史阶段记录。

2026-10-31 C3真实外设与发布策略见 [C3_REAL_BACKEND_20261031.md](C3_REAL_BACKEND_20261031.md)。native新增I²C/GPIO APB页、公共时间直连及显式620号坏点策略；50次RTL、C3专项、RV32与756项包检查PASS，物理管脚/P&R/上板未验收。C HAL rev2须重编译，默认MMIO关闭。

2026-10-31 真实历史数据接入：见 [REAL_DATA_REPLAY_20261031.md](REAL_DATA_REPLAY_20261031.md)。5张A真图已通过C2/DDR/CPU AXI回放和桌面对照，100条B热图已通过当前ABI及严格/B4策略对照；不是整机同步或上板推理。入口21_replay_real_team_data.cmd。

完整视频帧缓存与并发验收说明见 [VIDEO_FRAMEBUFFER_HANDOFF.md](VIDEO_FRAMEBUFFER_HANDOFF.md)。native内接GRAY8视频写入/显示读出与AI共用DDR，三缓冲按最终BRESP和A物理源帧记录发布。20_test_video_framebuffer.cmd运行49次回归；完整视频的逻辑接入不代表物理HDMI或板级时序已经完成。

当前源视频接入说明见 [SOURCE_VIDEO_CAPTURE.md](SOURCE_VIDEO_CAPTURE.md)：A采样器已接入native，时间在首DE锁存。控制接口保持APB v2.2，入口19_test_video_capture.cmd；下面sample_sof锁存方式保留为前阶段记录。

## 2026-10-25 统一时间与验收工具

当前接口为APB v2.2（0x00020002）；公共APB时间已接CPU/C3和视频快照CDC，C24新增串口采集/自检及现场窗口检查。42次RTL回归、时间后端测试、36个日志测试、新固件链接和native map PASS；没有实物执行。最新入口 [TIME_AND_C24_ACCEPTANCE.md](TIME_AND_C24_ACCEPTANCE.md)、18_test_time_c24.cmd。下方v2.1/39次为前阶段结果。

## 2026-10-25 联合链路

A缓存→C2桥、源端/DDR双完成、突发预取及C2→TFLM联合程序已有实现。39次RTL测试、主机联合流程、桌面回放及含A桥的native综合PASS；联合CPU固件ELF/BIN已构建，默认合成自检、现场MMIO关闭。入口 [C24_AC_BRIDGE_RUNBOOK.md](C24_AC_BRIDGE_RUNBOOK.md)、16_build_c24.cmd、17_test_a_c2_pc.cmd。新版APB v2.1（0x00020001）须配套使用，实际视频/共享时间/地址和上板验收仍待完成。

## 2026-10-24 开发入口

- C2第二阶段入口 [C2_VENDOR_APB_CACHE.md](C2_VENDOR_APB_CACHE.md)：厂家S0/S1接口适配、APB寄存器/CDC、CPU只读缓存接收驱动已实现；`13_test_c2.cmd`现运行34次RTL回归及主机/RV32检查。`15_synth_c2_native.cmd`用于独立厂家SoC接入副本的逻辑综合，板上视频/缓存/时序仍待验证。

- C2 第一阶段已新增共享内存功能边界：`projects/06_soc_c2`；18次RTL回归及Efinity逻辑综合PASS。交接详见 [C2_INTEGRATION.md](C2_INTEGRATION.md)，运行根目录 `13_test_c2.cmd`（仿真）/`14_synth_c2.cmd`（仅综合）。包含跨时钟图像传输、四源仲裁、完整帧写响应屏障及双槽管理；真实 SoC/IP、APB、缓存与上板验证仍待接入。

- 电脑端下一步已完成：C4_PC_RUNBOOK.md、PROGRESS_20261024_PC_NEXT.md；一键入口12_test_c4_pc.cmd。桌面模型兼容副本与原模型严格区分，补边策略已发现样图翻转，仍待A/C确认。

- 本轮主目录：C:\Users\16034\Downloads\FPGA\FPGA_2026_T3_P3；旧 D 盘路径仅作为历史日志保留。
- C1 诊断源码 c1/main.cc、上板说明 C1_RUNBOOK.md；构建入口为根目录 11_build_c1.cmd。
- C2/C3 交接入口 C2_C3_HANDOFF.md；共享接口 ../shared/interface_contract_v1.md 和 include/cooperation_v1.h。
- C3 实现 c3_hal/：已绑定现有 CLINT 时间源，I2C/GPIO 需真实后端，当前明确返回 ENOTSUP。
- 板卡暂时不在手边。本轮只做电脑端构建和测试，不声称已完成 C1 上板或 C2/C3 物理接入。

## 从哪里开始

- `projects/03_tinyml` 为已完整编译通过的 225 MHz 独立 SoC。
- `firmware/static_person_detect` 为已经构建的静态图片人体分类 CPU 程序，尚无板上执行证据。
- `docs/person_detect_firmware.md` 说明 CPU 文件、引导 ROM 和 Flash 布局的适用条件。
- 07 cmd 重建静态 CPU 固件；05 cmd 编译独立 TinyML FPGA。二者均不自动下载板卡。

## 必须优先的工作

1. 核对板型与实际 Flash 后，上板运行静态推理，保存 UART 的模型初始化、真实结果、时间和版本。
2. 第一天与 A 写出共享 DDR/总线/缓存设计，尽早进行实际读写验证。不能把已有两个 DDR 控制体系直接拼进同一板卡顶层。
3. 同时给 B 提供 I2C/GPIO/共享时钟的最小调用接口，不让传感器任务等待最终 AI。

## 后续交付

- 为 A 的实时 96×96 灰度图实现输入握手和实际模型预处理；记录帧号、校验值、推理分值和起止时间。
- 模型目前是全图有人/无人分类，不能直接当作人体框、姿态、跌倒或多目标模型。推理速率和视频帧率分别记录。
- 与 B 固定环境量/热特征参与融合的规则，再接实际三路快照。过期或缺失数据应标无效；需要改动已有融合模块时保留一致的状态行为和验证。
- 维护单目标运动轨迹，用真实时间间隔算速度并预测固定未来时刻位置。交付真实轨迹、预测点和误差，而不是仅画历史路径。
- 牵头另建整机工作目录；A 与 C 共同解决视频/DDR，B 与 C 对接传感器和网络。地址、寄存器、缓存和总线图由 C 汇总发布。
- 对整机重新评估资源/带宽/时钟/时序；实际调频须改 PLL 及对应约束，不能只放松时序声明。
- 发布可复现的 FPGA/CPU 配套文件、布局、工具版本、重新构建/下载/启动说明；请 A/B 按说明复现。
- 完成本人 AI/SoC/融合/预测/资源时序章节。最终报告排版由 B 汇总，技术数据由 C 自己负责。

## 关键验收

同一次上电里，CPU 读取的是当前摄像头帧，推理不阻塞视频；真实传感器有效，报警来自真实融合事件。最终配套文件能重复启动。只编译成功、打印旧静态结果、只展示一个独立工程都不算整机通过。
