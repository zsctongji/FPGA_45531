# 易灵思赛题三：多模态 AI 智能终端

2026-10-25 源视频采样增量：native顶层已接A的video_a_capture，输入改为单像素GRAY8/VS/DE，公共时间在首个有效DE像素锁存并保留到DDR描述符；不再用网格SOF改写时间。46次RTL回归、全帧桌面对照、新native综合和678项配套检查PASS。最新说明见 `team_work/03_ai_soc/SOURCE_VIDEO_CAPTURE.md`，入口19_test_video_capture.cmd。真实MIPI/HDMI、物理约束和上板仍待验收。

2026-10-25 后续更新：C2/C3 公共 APB 毫秒计数器、视频快照CDC和C24验收工具已实现；42次RTL回归及新版native综合PASS。APB升级至v2.2（0x00020002），旧固件不得混用。当前入口18_test_time_c24.cmd，说明见 `team_work/03_ai_soc/TIME_AND_C24_ACCEPTANCE.md`。物理时间/地址/视频和上板仍待验收。下方39次及v2.1为前阶段记录。

报名截图已确认：2026 FPGA 创新设计赛道，易灵思，赛题三“多模态 AI 智能终端”，平台“基于易灵思 FPGA 芯片的自制开发板”。用户提供芯片型号 Ti60F225，设备已有但尚未连接。

**当前已有五个独立 FPGA 调试工程和十二项通过的通用 RTL 自检，整机尚未完成。** LED、彩色摄像头、灰度摄像头、运动红框和 TinyML 225 MHz 均完整编译及最终时序检查通过，配置文件在 `fpga_bitstreams`。独立融合报警状态机已通过仿真；静态图片人体检测 CPU 固件及 4 MiB 引导 ROM 构建通过。尚无实体板实测，当前状态见 `docs/current_status.md`。

## 先打开哪些文件

2026-10-25：A→C2搬运桥及C2/TinyML联合固件已完成电脑端接入和验证，39次RTL回归、桌面读回推理对照、native逻辑综合PASS；联合ELF/BIN已构建，默认合成自检且现场MMIO关闭。入口16_build_c24.cmd、17_test_a_c2_pc.cmd，说明见 `team_work/03_ai_soc/C24_AC_BRIDGE_RUNBOOK.md`。APB需配套v2.1，实际视频/时间/地址/上板验收仍待完成。下文旧日期记录保留为历史结果。

2026-10-24 C组更新：主开发位置为 `C:\Users\16034\Downloads\FPGA\FPGA_2026_T3_P3`。C2共享DDR、厂家接口、APB及RX缓存后端已实现；34次RTL回归、主机/RV32检查及独立厂家SoC接入副本逻辑综合PASS，真实视频/物理映射/板上缓存/时序仍待验收。入口 `13_test_c2.cmd`、`15_synth_c2_native.cmd`；交接见 `team_work/03_ai_soc/C2_VENDOR_APB_CACHE.md`，最新记录见 `team_work/03_ai_soc/PROGRESS_20261024_C2.md`。C1诊断构建和C4桌面回放入口分别为 `11_build_c1.cmd`、`12_test_c4_pc.cmd`。下文五个工程的完整编译结果属于原有独立基线。

1. 双击 `01_check_environment.cmd`，查看开发工具检测结果。报告保存到 `logs/environment_summary.txt` 和 `logs/environment.json`。
2. 双击 `02_run_selftest.cmd`，运行全部基础模块自检。看到 `ALL PORTABLE RTL TESTS PASSED` 代表功能仿真通过；结果保存在 `logs/selftest.json` 与各个 `.run.log`。
3. 阅读 `docs/requirements.md`，它对应具体赛题任务并明确当前覆盖范围。
4. 阅读 `docs/board_bringup.md`，准备下一阶段板卡调试所需信息。

`03_compile_led.cmd`、`04_compile_camera.cmd`、`05_compile_tinyml.cmd`、`06_compile_camera_preprocess.cmd` 对应 LED、彩色摄像头、TinyML 和灰度摄像头四个工程，均已实际通过完整编译与最终时序检查。入口不烧录板卡；单独 `map` 综合成功只表示综合步骤通过。

`07_build_person_detect.cmd` 可重建厂家静态图片人体检测 CPU 固件，实际已构建成功。结果在 `firmware/static_person_detect`，日志为 `logs/firmware_person_detect.json`。该目录中的 HEX 是 CPU 程序，不能作为 FPGA 配置文件直接下载。实时摄像头、传感器和板上推理仍待集成/验证。

`08_test_led_key.cmd` 检查 LED 按键逻辑。`09_test_motion_fusion.cmd` 运行新增的五项运动/融合自检；`10_build_camera_motion.cmd` 重建灰度帧差红框工程，已实际通过完整编译。说明在 `docs/motion_fusion.md`。全部十二项自检仍可通过 `02_run_selftest.cmd` 运行。

命令文件结束后保留窗口，便于看清输出。若失败，不用重装全部软件，将 `logs` 中的结果提供给协助调试的人即可。当前脚本不打开串口、不下载 FPGA、不操作板卡电源。

## 目前工程包含什么

| 文件夹 | 内容 |
|---|---|
| `rtl` | 灰度、二值化、Sobel、传感器滤波/对齐、帧差统计、视频红框和独立融合报警模块 |
| `sim` | 与算法参考值比较的 SystemVerilog 自检台，不依赖物理板卡 |
| `tools` | 环境检测、自动仿真入口、项目内仿真工具及其来源/许可 |
| `docs` | 接口说明、真实完成状态、板卡接入步骤与待获取资料 |
| `references` | 2026 易灵思赛题 PDF 镜像及来源核验记录 |
| `projects` | D 盘中的 LED、摄像头直通、TinyML、摄像头预处理、运动红框五个工作工程 |
| `vendor_projects` | D 盘中的厂家资料原始解压副本 |
| `vendor_archives` | D 盘中的厂家压缩包及软件发行包 |
| `firmware` | 实际生成的静态图片人体检测 CPU 固件及适用说明 |
| `fpga_bitstreams` | 五个独立工程实际生成的 FPGA 配置文件，三模态整机程序仍待集成 |
| `logs` | 实际工具检测和仿真日志 |
| `build` | 重跑测试时产生的缓存，可在关闭测试程序后删除 |

## 下一步实现方向

暂按“非授权时段入侵预警”场景设计：摄像头提供人体位置和运动，红外阵列验证热特征，温湿度提供环境信息，软核完成本地轻量 AI 和融合，HDMI 显示结果，LED/蜂鸣器报警。暂选网络事件上报和行为轨迹预测作为两个拓展方向。这是工程选择，不是已经完成的功能，也不替代真实模型训练和评估。

图像灰度/二值化/Sobel属于预处理，**不等于人体检测 AI**。两源采样对齐模块**不等于完整视频、红外阵列、环境三路同步系统**。传感器标量滤波也**不等于 MLX90640 温度校准**。这些模块还需要连接到实际 MIPI、DDR、I2C、显示和 Sapphire RISC-V 系统。

## 开发工具

Ti60 使用易灵思 **Efinity**。2026.1.132 位于 `D:\FPGA_2026_T3_P3\tools\efinity\2026.1`，未修改系统 PATH 或安全设置。初期直接导入 Interface Designer 的 QtGui.pyd 被 Windows 拒绝；2026-10-18 通过本项目 .cmd 的普通 Windows 启动入口，实际接口流程已通过。历史诊断保留，按当前日志判断结果。

软件入口：[易灵思中国 Efinity](https://www.elitestek.com/efinity/)，[Efinix Efinity](https://www.efinixinc.com/products-efinity.html)。原厂下载/许可证需用户账户及下载资格；申请和登录由账户本人处理。可向板卡提供方获取对应软件版本及已验证的例程包。

仿真可使用项目内 Icarus，或其他可用的仿真器。受限运行环境曾导致 Vivado 2018.3 编译器出现 DLL 启动错误；改在正常运行环境下已完成全部 XSim 自检，无需重装 Vivado。失败和成功记录均已保留。

## 测试数据使用方式

`logs/selftest.json` 的 PASS 仅代表列出的输入序列与参考算法一致，并记录对应源码哈希。1280×720 和 1920×1080 的测试帧尺寸通过，不等于摄像头帧率实测通过。五个独立工程已有综合和最终时序报告，尚无整机资源、实际帧率、识别准确率、功耗或端到端延迟；最终报告需从真实板卡运行采集。

赛题要求来自 21 页 PDF 镜像，未与赛事官网的原始文件哈希核对，来源限制已记录在 `references/SOURCES.md`。同为 Ti60F225 芯片的不同开发板管脚不能混用；该指南还明确区分推荐板和 VF 开发板使用范围，须核实实际板型。
