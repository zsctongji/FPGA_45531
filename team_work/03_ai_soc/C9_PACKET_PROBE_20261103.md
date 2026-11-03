# CSI 包与边沿探针（2026-11-03）

当前状态：完整版综合通过，但打包需要60878 XLR，超过60800容量78，未生成/加载位流。失败证据保留；精简版正在独立构建。

背景见 C9_CSI_BOARD_20261103.md：旧 geometry 镜像复现 72 像素短段；新 PHY 计数探针实板表现不同且计数饱和，不能据此确定像素修复。

本探针从旧 geometry 镜像隔离构建。原像素路径和控制配置不改，只把原生 CSI 的 word_count、datatype、pixel_per_clk、vc 接至诊断记录，计数原生 VS 上升沿及每个 VS 区间的 HS 上升沿。

## 独立 PHY 快照协议

bank4、pair0 的 lo：bit31 metadata_seen、30 metadata_changed（有效 payload 期间元数据曾改变）、29 valid_outside_hs、28 原 camera_fault；27:26 VC、25:22 pixel_per_clk、21:16 datatype、15:0 word_count。元数据只在原生 pixel_data_valid 时更新。

hi：31:20 VS 上升沿累计数（12 位饱和），19:8 上一个完整 VS 区间 HS 上升沿数（12 位饱和）；bit7 当前VS、6 当前HS、5 当前valid、4 已观察完整VS区间、3 VS计数饱和、2 上一区间HS计数饱和、1保留零、0协议标记1。

元数据是最近的有效 payload，HS 数是上一个完整 VS 区间，两者未必属于同一包。原生与 C2 等其他时钟域的不同 pair 也不是同一瞬间。两个字复用旧 PHY debug 的位置，必须使用 packet 固定镜像对应解码器，不能当旧 debug 字解释。

## 工具入口

- `tools/test_c9_packet_probe.py`：1080 HS、长时间 HS、元数据变化、HS外valid、计数饱和、复位仿真。
- `tools/test_c9_packet_decode.py`：字段解码、异常保留与非法协议拒绝。
- `tools/run_c9_packet.ps1`：仅电脑构建，不执行下载。
- `tools/audit_c9_packet.py`：受控源码变更、引脚/时钟/DDR、时序和66位Gray CDC核对。
- `tools/report_c9_packet.py`：生成诊断包和离线身份检查。
- `tools/run_c9_packet.py`：默认只核对本地身份；显式 `--capture --port COM13` 才执行实板诊断，结束恢复C10。

固件仍为冻结的3508字节 c9geom-3bcf05e8d3894dc3，完整回读后才运行。`tools/check_c9_packet.py` 将原生观测完整与 C2 视频验收分开：原生VS不进展、未形成完整区间或计数饱和时保留 INCOMPLETE_PACKET_OBSERVATION；即使诊断完整，也不声称真实视频通过。原有视频验收标准没有放宽，active profile 不推广为此镜像。

静态对比记录 logs/c9_geometry_implementation_comparison_20261103.json 已确认旧geometry与前一PHY探针：厂家源码、像素适配RTL、约束、生成时钟声明和引脚一致。这只能排除这些静态配置差异，不能证明放置/布线行为或启动状态相同。

实际构建与上板结果须以独立日志为准。未改DDR参数、校准算法、1920×1080或坏帧拒绝；不写Flash。

## 精简版独立协议

`c9_packet_probe_compact.sv` 与 `build/c9_packet_compact_image_20261103` 使用独立协议：lo bit31是最近有效payload元数据已记录、bit30是当前VS、bit29当前HS、bit28原camera_fault；27:0的VC、PPC、datatype、word_count布局不变。hi为 `0xc9c20000 | (vs_edge_mod16 << 4) | hs_edge_mod16`。

两个边沿计数只保留低4位，会回绕。相同数值不能证明没有活动，也不能从该数值恢复完整行数或频率。精简版没有 metadata_changed、valid_outside_hs 或完整VS区间行数。必须使用 `check_c9_packet_compact.py`，不能套用完整版或旧PHY解码器。

对应工具：`test_c9_packet_compact.py`、`test_c9_packet_compact_decode.py`、`run_c9_packet_compact.ps1`、`audit_c9_packet_compact.py`、`report_c9_packet_compact.py`、`run_c9_packet_compact.py`。默认运行器仍只核对本地身份，显式 `--capture --port COM13` 才访问板卡，并在结束后恢复C10。分轮测量包格式与完整行数是资源限制下的取舍，不改变视频验收要求。

## 本轮结果与限制

完整探针因60878/60800 XLR超限停止，未上板。精简版60555/60800 XLR、RAM224、DSP60，setup +0.061 ns、hold +0.016 ns，66位Gray CDC两角通过；位流 SHA256 e6637e93edccaa5232e9a3ed852932e7508d6f17cfac4bd5edb633ce1011ed20。

两次精简版实板校准和3508字节固件完整回读通过：114336记录wc=2400、dt=0x2B、PPC=4、VC=0；114725记录wc=2400、dt=0x2B、PPC=2、VC=0。两次C2均width=0，分别294/293和241/240个源边界/格式错误，AI完成0，未通过视频。PPC是最近一次valid的采样，不是全帧分布；不能据此断言所有拍均为2或4。

初次主机checker遗留packet实验名，而实际variant是packet_compact，导致身份误报。原checker及初次失败result保留；独立check_c9_packet_compact_v2.py修正名称后离线重放通过，错误variant、错误镜像、错误完整回读均仍被拒绝。身份回归记录 logs/c9_packet_identity_tests_20261103.json。后续必须使用run_c9_packet_compact_v2.py和v2 checker，原离线诊断包的host脚本属于历史版本，不要直接复用。

最终C10恢复记录 logs/c10_warm_boot_20261101/20261103_114748/attempt.json，六组静态推理通过；未写Flash，未改变active profile，没有物理断电冷启动或真实视频通过结论。

### 官方资料核对与下一步

核对资料：[Efinix MIPI 2.5G CSI-2 RX UG v2.7](https://www.efinixinc.com/docs/mipi-2-5g-csi2-rx-core-ug-v2.7.pdf)，表6/7/9/15/19以及Pixel Clock Calculation。该版说明PPC仅在valid高时有效，RAW10常规编码为每拍4像素；像素时钟过高可能让FIFO读空、valid行内断续。这支持排查速率匹配/行缓冲的假设，尚非实板根因证明。

该新版将word_count/datatype/vc列入字节时钟域状态，pixel_*sideband才属于像素时钟域。当前观测器在pixel时钟域直接取旧包头状态，不能把组合记录当作已验证CDC的一拍包头；2400/0x2B仅是重复一致的粗粒度观察。当前厂家封装没有引出pixel_*，内层源码存在这些接口的条件声明，本地SDK该IP版本5.15；还需核对实际生成IP配置/版本与sideband支持，不能只根据新版文档强认所有信号约定。

下一步：优先采用所用IP支持的pixel_* sideband或有协议的跨域快照；再统计每个valid拍的PPC分布、像素总数和行/帧边界，确认2是尾拍、动态有效数量还是其他现象。维持DDR、1920×1080和坏帧拒绝；不盲目拼接像素，不因FIFO假设直接调整时钟。此阶段像素路径尚未修复。

机器结果 logs/c9_packet_board_result_20261103.json，离线重放 tools/report_c9_packet_board.py；静态差异检查 logs/c9_geometry_implementation_comparison_20261103.json。源文件、诊断包和公开日志已复制到本地交接仓库，未提交/推送GitHub。
