# 当前工程状态

更新日期：2026-10-19（北京时间）。实际工作目录为 `D:\FPGA_2026_T3_P3`；聊天输出目录保留算法、说明和日志副本，大型厂家包及 Efinity 仅在 D 盘。

| 项目 | 实际结果 | 待完成 |
|---|---|---|
| 通用 RTL | 十二项 Icarus 自检 PASS，含两帧 1280×720 和两帧 1920×1080；原六项也通过 XSim | 实体板验证 |
| Efinity | 2026.1.132 已部署；普通 Windows .cmd 入口实际跑通综合、Interface Designer、布局布线及配置文件生成 | 实物连接与运行 |
| LED | 修复时钟切换、复位和消抖；单独按键测试通过，完整 FPGA 编译 PASS | 上板观察 |
| 摄像头预处理 | 三种 HDMI 模式对齐自检通过；灰度副本完整 FPGA 编译 PASS | 摄像头/显示器实测 |
| 彩色摄像头对照 | 独立直通工程完整编译 PASS，保留作彩色/灰度比较 | 摄像头/显示器实测 |
| TinyML 硬件/软件 | 225 MHz SoC 完整 FPGA 编译 PASS；CPU 固件交叉编译 PASS；4 MiB 引导 ROM 构建 PASS | 实时摄像头输入和真实板上推理 |
| 摄像头运动红框 | 96×54 灰度帧差接入显示链路；第五个独立 FPGA 工程完整编译及最终时序 PASS | 真实画面、阈值调整、帧率及红框实测 |
| 融合报警逻辑 | 视觉/红外/环境证据加权、有效期检查、重复帧过滤、确认、报警保持及事件字段仿真 PASS | 真实传感器和 AI 输入、跨时钟/总线接入、场景校准及物理输出 |
| 三模态整机 | 比赛任务、资料和候选架构已核对；运动显示工程和独立融合模块已有代码 | 真实采样、实时 AI、融合连接、物理报警、两项拓展、实测及提交材料 |

2026-10-19 新增 `projects/05_camera_motion`：保留厂家 MIPI/DDR/HDMI、外围配置和时钟，在灰度视频中加入帧差红框。完整 map/interface/pnr/pgm 通过，最终最差 setup/hold 为 **0.534/0.026 ns**，新生成 HEX 已归档到 `fpga_bitstreams/camera_motion`。`09_test_motion_fusion.cmd` 可运行五项新增自检，`10_build_camera_motion.cmd` 可重建此 FPGA 工程。详见 `docs/motion_fusion.md`。

全部十二项自检已于本日从 D 盘执行通过，结果及 RTL/测试台 SHA256 在 `logs/selftest.json`。其中 1080p 运动测试处理 4,147,200 像素、10,368 网格样本，准确得到 32 个变化点及预期差值和/边界框；这是功能仿真，不是实体采集或帧率测量。

## 独立工程综合资源

2026-10-18/19 Efinity 2026.1.132 工作工程实际报告：

| 工程 | LUT4 | FF | DSP48 | RAM10 | 其他存储 |
|---|---:|---:|---:|---:|---|
| 摄像头 + 灰度预处理 | 18,514 | 11,275 | 4 | 86 | DPRAM10 4，SRL8 1,164 |
| TinyML 225 MHz + 新引导 ROM | 27,648 | 23,261 | 47 | 144 | SRL8 840 |
| 摄像头 + 灰度 + 运动红框 | 18,794 | 10,979 | 4 | 94 | DPRAM10 4，SRL8 1,164 |

表中是独立工程。各自有 DDR/时钟/外围配置，不能直接叠加为已经跑通的整机；集成时须共享 DDR 和总线资源。运动逻辑已映射到 8 个额外 RAM10；其变化区域是帧差区域，不能称为人体检测框。尚无整机资源利用率、运行频率、实物帧率、功耗或 AI 准确率。

## 真实编译验收与历史问题

Efinity CLI 捕获 Interface Designer 的 ImportError 后可能跳过步骤并仍返回 0。首轮 LED 日志写有 `Missing Interface Designer LPF constraint file, no programming file will be generated.`，还有 -1.567 ns / -1.132 ns 跨时钟 setup 负裕量。原始退出码记录仅用于诊断，不能作为成功证据。

已加入组件预检、文件新鲜度、LPF/HEX 存在性及最终 STA 检查。按最终时序报告验收 setup/hold 裕量，不把布线前已修复的 hold 告警误作最终失败，也不把旧厂家文件或工具零退出码作为成功证据。2026-10-18 四个工作工程均已实际通过完整流程。

初期直接导入 QtGui.pyd 被 Windows 拒绝，历史 Code Integrity 事件已保留。2026-10-18 使用本项目 .cmd 的普通 Windows 启动入口，组件预检和实际 Interface Designer 流程均通过；未改动 Windows 安全设置。推荐使用已验证的 .cmd 入口，旧诊断文件不代表当前流程仍失败。

最终时序：LED 最差 setup/hold 为 10.381/0.097 ns；彩色摄像头为 0.448/0.026 ns；灰度摄像头为 0.492/0.026 ns；TinyML 225 MHz 为 0.144/0.026 ns；运动红框为 0.534/0.026 ns。均限于工具成功应用的厂家约束和指定时序模型。厂家约束中仍有 `ddr_addr[15]` 未匹配端口等告警，当前结果不能证明全部外部接口约束完整或实物时序通过。完整报告保存在各工程 outflow，摘要在 logs/verified_artifacts.json。

TinyML 厂家配置的 300 MHz 路径曾出现 -0.241 ns setup 裕量；实际将 i_sysclk PLL 输出分频 9 改为 12，得到 225 MHz，并同步约束为 4.444 ns。CPU和加速器同用该时钟，内存/外围/CLINT 保持 100 MHz，DDR PHY 保持 400 MHz。未增加 false/multicycle path 来掩盖该路径。

## 已生成的人体检测 CPU 固件

2026-10-18 使用项目内 xPack RISC-V GCC 13.4.0 实际构建成功，记录为 logs/firmware_person_detect.json。BIN 为 1,417,720 字节；ELF32 RISC-V、入口 0x1000；linker 报告 RAM 使用 3,686,880 字节（包含预留栈）。来源是厂家 MobileNet 静态图片例程，输入 96×96 灰度，输出有人/无人分数，尚未执行实际推理。

CPU 文件在 `firmware/static_person_detect`；FPGA 配置文件在 `fpga_bitstreams`。CPU HEX 不能当作 Ti60 FPGA 配置文件烧录。新引导程序为 664 字节，放入 4096 字节 ROM，支持从 Flash 0x380000 复制 4 MiB 到 RAM 0x1000。实际板型/Flash 容量和下载流程尚须核对；未生成或写入完整 Flash 合并镜像。详情见 docs/person_detect_firmware.md。

## 实物信息

包装确认厂家为炫览科技，用户确认免费申请板和 Ti60F225。PCB 版本、摄像头模组、红外阵列和温湿度传感器尚待核对。2026-10-19 只读 USB 枚举仍未发现匹配的 FTDI/JTAG 下载器，结果在 `logs/device_inventory.json`。上板前须确认实物与 V4 原理图/电压/外围配置相符。未打开串口、操作电源或烧录板卡。
