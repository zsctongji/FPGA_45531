# C：RISC-V/TinyML、统一工程、融合与预测

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
