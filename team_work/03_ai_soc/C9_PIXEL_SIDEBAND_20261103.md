# 像素域 sideband 观测（2026-11-03）

本轮先纠正诊断接口的时钟域，不改像素路径、DDR或视频验收条件。随后为满足资源限制，独立诊断配置将解包格式收窄为Pack40，细节与适用范围见后文；正式active profile不变。

## 实际IP封装核查

本地厂家源码 `csi_rx_controller.sv` 内层 `efx_csi2_rx` 和 `efx_csi2_rx_top` 已声明并传递 `MIPI_CSI2_RX_PIXEL_SIDEBAND` 条件端口；原外层封装未引出。本轮只在私有构建副本启用该宏、导出 pixel_wordcount/pixel_datatype/pixel_vc，所有加密IP内容与其余尾部逐字节保持原样，原PACK_TYPE、tINIT、FRAME_MODE等参数不变。公开工具是转换脚本，不包含厂家完整源码。

依据 [Efinix 官方 UG v2.7](https://www.efinixinc.com/docs/mipi-2-5g-csi2-rx-core-ug-v2.7.pdf) 表7/9，旧word_count/datatype/vc属于字节域状态，pixel_*是像素域sideband。不能用直接在pixel时钟采样旧状态的记录认定同拍包头。当前补丁连接的是实际内层现有pixel_*接口，而非自行对异步总线打两拍。

另一个限制：现有顶层AXI调试时钟与复位固定零，官方文档把debug输出列为该域信号，因此此前debug=0、camera_fault=0不是无CRC/同步错误的证据。本轮保持这部分不改；需要错误统计时应另行启用有效的调试域/CSR通路。

## 新探针

c9_sideband_probe在原生像素时钟域工作。APB RUN经两个async_reg触发器同步后才开始记录。仅pixel_data_valid高、pixel_datatype=0x2B、pixel_vc=0时记录图像PPC集合和最近字节数；其他有效类型/VC只置独立标志。集合不是频率分布或逐帧计数。

PHY bank4/pair0 lo：bit31图像已记录、30存在其他有效类型/VC、29存在图像valid高且HS低、28原camera_fault；27:26选定VC0、25:22最近图像PPC、21:16选定类型0x2B、15:0最近图像pixel_wordcount。类型/VC由捕获条件保证，未见图像时不能把这些常量当测得值。

hi：31:16协议标记0xC9D1，15:0为PPC出现集合，第n位表示RUN后至少出现一次符合条件的PPC=n；包括零或异常值，不会静默丢弃。未启用RUN时观测清零；原生探针与C2不同域快照不保证同一瞬间。

专项仿真覆盖RUN单比特同步、PPC=4/2集合、其他类型与VC排除、valid在HS外、零PPC、无效周期不污染和复位。真实外层封装接线用接口桩验证：故意把旧字节状态设成错误值，确认pixel_*正确转接；不声称模拟了厂家加密CSI行为。

## 入口

- 生成/编译：tools/prepare_c9_sideband.py、tools/run_c9_sideband.ps1。
- 只读源码/物理审计：tools/audit_c9_sideband.py。
- 包与默认离线身份核对：tools/report_c9_sideband.py、tools/run_c9_sideband.py。
- 实板必须显式 `tools/run_c9_sideband.py --capture --port COM13`；先校准状态、固件完整回读，再RUN采集，结束恢复C10，不写Flash。
- 解码：tools/check_c9_sideband.py。CAPTURED_SIDEBAND_STATUS_ONLY不表示视频/TinyML验收通过。

原旧镜像与历史失败记录保持冻结，正式active profile不改变。实际构建和实板结论须等本版独立证据。

## 资源受限版本

完整sideband观测器已通过综合，但打包需要60816/60800 XLR，超过16；失败日志保持原样，没有生成或加载位流。第二版 `c9_sideband_probe_small.sv` 去掉最近PPC寄存器，PPC集合只保留0/1/2/3/4五项；更大的值统一保留为异常标志，不静默忽略。

第二版协议：hi高16位0xC9D2，bit15表示图像PPC>4曾出现，bit4:0为PPC0..4出现集合，bit14:5保留零；lo沿用图像seen/其他payload/图像valid在HS外/fault标志及WC，PPC四位位置改为保留零，没有“最近一次PPC”值。图像seen从集合或异常标志导出。需使用check_c9_sideband_small.py，不能混用0xC9D1解码器。不同PPC出现的频率和是否尾拍，仍需另行计数/抓取。

对应生成/构建/审计/报告/运行工具分别加 `_small`：prepare_c9_sideband_small.py、run_c9_sideband_small.ps1、audit_c9_sideband_small.py、report_c9_sideband_small.py、run_c9_sideband_small.py。本地重放实板结果使用report_c9_sideband_board.py。

## Pack40诊断配置

保留全部格式的小观测器仍因全局优化后的61114/60800 XLR而失败，未生成/加载位流；减少寄存器并未带来单调的布局资源下降。两次失败证据保留。

随后采用本地IP组件明确支持的PACK_TYPE=1：只启用Pack40，保留RAW10/RAW20/YUV420-10/YUV422-10类别，禁用Pack48、Pack56、Pack64。SDK组件的掩码表达式与SHA256保存在logs/c9_pack40_mapping_20261103.json。不是修改DDR参数，也不是放宽视频格式验证；其余IP参数、引脚、时钟、复位与像素连接保持原值，加密IP尾部仍逐字节保留。

此配置可观测RAW10 VC0，不能把“其他payload标志为零”当成被禁用格式不存在的证明。整机若需要其他输入格式，必须分别验证并恢复相应解包支持。原默认active profile未更改，旧全格式位流保持冻结。

本配置入口为prepare_c9_sideband_raw10.py、run_c9_sideband_raw10.ps1、audit_c9_sideband_raw10.py、report_c9_sideband_raw10.py、run_c9_sideband_raw10.py、check_c9_sideband_raw10.py；默认仍只做离线核对，显式--capture才接板，结束恢复C10。解码协议沿用0xC9D2，但host严格绑定独立variant sideband_raw10和位流/审计/固件身份，不能套用其他variant记录。

## 已完成：seed3物理实现与两轮板测

Pack40配置的seed2完成综合与打包（60217 XLR），但布线拥塞，停止该次P&R并保留日志，没有加载该版本。seed3沿用同一份综合结果：108个编译源文件逐项SHA256相同，工程规范化比较仅允许输出路径和P&R seed变化；MAP_REUSE.json绑定复用文件。seed3通过P&R、STA和66位Gray CDC双角检查：60217/60800 XLR、224 RAM、60 DSP，最小setup +0.170 ns、hold +0.026 ns。

最终诊断包 `fpga_bitstreams/c9_sideband_seed3_100mhz`，位流SHA256 `333af57e423c4174aaf0b1d0589b6a0c796f85ea530758f0fc715528896328b2`。入口为tools/run_c9_sideband_seed3.py；其默认模式只核对身份，显式--capture才访问板卡。它使用原3508字节geometry固件（SHA256 f9955a3639543272716f1ef998156f6aae05d297c8841eb7092af8ef57ced9a5），不改变视频数据路径或验收标准。

构建时曾缺少Interface Designer LPF，Efinity外层返回PASS但未生成位流；审计以缺失位流判失败。补齐同源、相同接口工程的LPF后重做bitgen并审计通过，LPF_REUSE.json保留来源。首次板测因主机缺少USER2 BSDL文件而中止，未取得校准状态，不计DDR失败；补齐同源文件，HOST_ASSETS.json绑定来源。失败记录与每次C10恢复记录均保留，未覆盖原失败结果。

同一合格seed3位流的两次重新配置结果如下（每轮RUN后约10秒）：

| 项目 | 13:00:37采集 | 13:08:18采集 |
|---|---:|---:|
| DDR校准、固件完整回读 | 通过 | 通过 |
| 最近图像pixel_wordcount | 2400 | 2400 |
| 图像筛选类型/VC | RAW10 0x2B / 0 | RAW10 0x2B / 0 |
| RUN后图像PPC集合 | 仅4 | 仅4 |
| 图像valid高且HS低 | 未记录到 | 未记录到 |
| C2源帧边界 / 格式错误 | 244 / 243 | 238 / 237 |
| 最近C2最大连续DE宽度 | 0 | 72 |
| 最近C2 DE段数 | 0 | 超过4095，饱和 |
| 完整帧 / AI完成 | 否 / 0 | 否 / 0 |

以上只说明本Pack40配置的两个观测窗口，不能证明旧全格式配置的PPC=2是伪读、所有包字节数都为2400、或CRC/同步正常。相同位流仍出现C2宽度0与72，启动顺序、复位释放和流时序也应检查，不能仅归因于布局不同。快照跨域不保证同一拍；PPC集合不是逐帧分布。

最后恢复C10并通过六组静态TinyML：`logs/c10_warm_boot_20261101/20261103_130842/attempt.json`。这是暖启动恢复，不是本轮物理冷启动；未写Flash，未修改DDR参数/校准算法/active profile。真实视频仍未通过，物理HDMI显示也未验收。

离线复核全部三次父流程（含主机失败）用 `tools/report_c9_sideband_seed3_board.py`，汇总为 `logs/c9_sideband_board_result_20261103.json`。下一步沿RAW串并转换、ISP、灰度输出到C2入口逐级增加同域DE/valid与复位状态观测，定位信号在哪一级丢失或切碎；现有证据不足以安全修改像素拼接、行宽常量或坏帧拒绝规则。
