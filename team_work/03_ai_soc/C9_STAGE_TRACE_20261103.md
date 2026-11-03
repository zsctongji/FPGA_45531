# RAW、ISP、灰度与C2分级检查

这是独立Pack40诊断实验，基于已冻结的sideband_seed3。原合格镜像、DDR参数/校准、引脚、PLL、像素处理与源门控均保持原样；正式active profile仍为display。新的物理构建和实板结论以各自记录为准，下面的合成激励不是传感器实测。

## 可区分的假设

1. 若原生CSI有效负载已有间隙或RAW跨时钟转换产生间隙，首个连续段长度下降应出现在native或raw_2ppc；后级可能继续原样传播碎段。
2. 若ISP的DE和valid错位，则两者单独有数据，而联合有效段显著缩短或消失；灰度入口随后失去数据。
3. 若最终故障门控或源启动状态截断数据，则pixel_1ppc仍有数据，而source_1ppc消失；同时核对fault、RUN、config_valid和共享时间valid。所有探针由camera_reset_n复位，快照本身不能证明整个窗口从未发生公共复位。

## 本地实际链路仿真

`tools/test_c9_stage_chain.py` 使用冻结镜像的physical_pixel_split、厂家A的明文ISP、physical_gray2和video_a_capture，未用简化模型替代这些模块。加密CSI核不在仿真范围。三个时钟为50/100/200 MHz，连续输入另测0/1/3 ns相位差；每组3帧、1920×4。

| 激励 | native最长拍数 | RAW/ISP/灰度2PPC最长拍数 | pixel/source最长拍数 | 采集结果 |
|---|---:|---:|---:|---|
| 连续RAW10（3种相位） | 480 | 960 | 1920/1920 | 3个完整帧，0格式错误 |
| 每18个RAW拍插入1拍空隙（2种相位） | 18 | 36 | 72/72 | 0完整帧，3格式错误，连续宽72 |
| 仅在ISP输出边界屏蔽valid | 480 | RAW与RGB DE为960，RGB valid/联合/灰度为0 | 0/0 | 0完整帧，3格式错误 |
| 仅开启最终故障门控 | 480 | 960 | 1920/0 | 0完整帧，3格式错误 |

七组均符合预期。72像素碎段可由合成间隙复现，但这不是实板根因证据。另有计数器饱和不回卷、RUN前清零、重启、异步复位和解码器错误标记/保留位拒绝检查，见logs/c9_stage_chain_tests_20261103.json、logs/c9_stage_decode_tests_20261103.json。

## 只读探针与协议

源码 `c9_live/camera_geometry/c9_stage_probe.sv`。每个域用独立的两级RUN单比特同步器。DE连续拍数与段数在同域累积，RUN前清零；最大拍数饱和于2047，段数饱和于4095，解码为“至少该值”，不回卷。RUN若在有效段中间开启，首段可能是截段。记录窗口为RUN后至快照，不是逐帧/逐HS行计数。

每个24位计数字段：bit23保留零，22:12最长连续拍数，11:0有效段数。native为4PPC，RAW/ISP/gray为2PPC，pixel/source为1PPC；只有PPC稳定且没有其他类型混入时才能按此换算像素数。不同域与不同快照pair不保证同时采样，不能据此严格比较全窗口总量。

- PHY bank4：63:56标记0xE1；55为RUN同步态；bit54 raw_overflow曾出现、53其他有效类型/VC、52图像非4PPC曾出现、51图像valid在HS外、50图像seen、49 HS seen、48 VS seen；47:32最近RAW10 VC0字节数；31:24保留零；23:0为native图像DE且HS有效的计数。
- 原camera bank3改由pixel2_clk快照160位ISP探针，**不再是I²C寄存器**。从低位起5个24位计数分别为raw_de、rgb_de、rgb_valid、二者联合、gray_de；127:120为RUN及VS/mismatch/overflow/RAW seen标志，159:128为0xC9E21001，其余高字为零。同步raw_overflow后才在该域记录。
- 视频bank1 word6替代原pattern_completed：31:30标记2；29/28/27为source DE/source VS/pixel VS曾出现，26共享时间valid、25配置valid、24故障门控、23pattern模式、22 RUN同步态；21:11 source最长拍数，10:0 pixel最长拍数。word7原geometry flags不变，其他C2计数不变。

继续使用原3508字节geometry固件及完整回读：它只负责MAP、RUN和快照。其打印的geometry声明仍适用于word7，不能据此把重用的camera bank或word6交给旧解码器。新主机checker严格绑定stage variant及位流/审计/固件身份。debug域仍关闭，不能从无fault标志推断无CRC/同步错误。

## 操作入口

- 本地仿真：tools/test_c9_stage_chain.py、tools/test_c9_stage_decode.py。
- 新建隔离工程：tools/prepare_c9_stage.py；编译：tools/run_c9_stage.ps1。
- 物理/源码/时钟/引脚审计：tools/audit_c9_stage.py；打包：tools/report_c9_stage.py。
- 默认离线核对：tools/run_c9_stage.py；显式--capture --port COM13才访问板卡，先核对校准、完整固件回读，再采集，finally恢复C10。没有Flash写入操作。
- 解码：tools/check_c9_stage.py。CAPTURED_STAGE_STATUS_ONLY只表示取得诊断证据，不能作为真实视频或TinyML通过。

## 轻量诊断配置

保留TinyML的stage版已综合、打包到60494/60800 XLR（99.5%），布线过程中仍有较多拥塞，主动停止以缩短本次反馈循环；未生成合格位流、未加载板卡，也不据此声称该设计无法布通。停止记录见logs/c9_stage_full_stopped_20261103.json，原流程输出保留。

stage_min版使用完全相同的分级探针与四个像素处理实例，只在私有physical_soc_core.v副本移除TinyML实例，把该主机的AXI输出保持空闲、自定义指令握手保持不接受，不返回伪造计算结果。CPU、C2、DDR控制器和源/视频路径保持原逻辑。原3508字节固件不调用加速器；它的MAP和快照仍须实际跑通，不能由这个假设代替执行证据。轻量版没有TinyML能力，不能用于CPU/TinyML/视频并发验收；只用于定位视频链路，最后恢复完整C10。

轻量版入口是prepare_c9_stage_min.py、run_c9_stage_min.ps1、audit_c9_stage_min.py、report_c9_stage_min.py、run_c9_stage_min.py、check_c9_stage_min.py。协议相同，但variant、位流和审计身份独立绑定，不得拿stage_min日志套用stage或旧sideband验收。源审计除显式的TinyML实例替换外逐项比较编译源，DDR/引脚/时钟不允许变化。实际物理与板测结果见后续证据。

## 结果：已在实板定位最早观测到的碎段边界

轻量版通过综合、P&R、STA、66位Gray CDC双角与源码/引脚审计：30823/60800 XLR，最小setup +0.319 ns、hold +0.025 ns。位流SHA256 `0179b3e7d9a60655cf668c4828f670efe2e4927194cd7ded9fbd7a10e2b1f048`，审计SHA256 `35383a485d714c161fe95f75c37c4731fc2a378ab3fcc6b33bc43dcd4db2021a`；包为fpga_bitstreams/c9_stage_min_100mhz。静态ELF检查的720条可执行指令没有加速器custom opcode，保留两处原cache invalidate指令；实际MAP和完整固件回读也通过。

用户重新连接原USB口后，COM13/JTAG恢复。两轮各自重新配置、采集约10秒并恢复C10：

| 阶段 | 16:02:15采集最长连续拍数 | 16:04:56采集最长连续拍数 | 按所测PPC换算 |
|---|---:|---:|---:|
| CSI原生RAW10 VC0，DE且HS | 18 | 18 | 72像素 |
| RAW转换后2PPC | 36 | 36 | 72像素 |
| ISP DE | 36 | 36 | 72像素 |
| ISP valid | 36 | 36 | 72像素 |
| ISP DE且valid | 36 | 36 | 72像素 |
| 灰度2PPC | 36 | 36 | 72像素 |
| 最终pixel_de 1PPC | 72 | 72 | 72像素 |
| source_de / C2入口1PPC | 72 | 72 | 72像素 |

两轮native未记录到图像非4PPC、其他有效类型/VC或图像valid在HS外；最近WC均2400。RAW FIFO未记录到overflow；ISP未记录到DE/valid单独为高的错位；最终故障门控未置位，RUN、配置valid、共享时间valid均有效。native与ISP各DE计数的段数均饱和于4095，表示至少4095段，不能当成精确段数。

据此可以把本次观测中的首个碎段边界定位到**CSI像素输出侧，早于RAW转换/ISP**；其后各级保留相同的72像素最大段长。实际A ISP的line_buffer/raw_to_rgb使用DE下降沿作行处理边界，因此这种节奏与当前“完整连续DE行”的接入方式不兼容。现有记录没有显示ISP进一步缩短最大段或最终门控吞掉所有输入，不能据此证明所有帧、所有实现的这些环节都正常。

最新C2记录仍分别为：宽72/段数饱和、宽0/段数0；窗口源帧/格式错误分别252/251、297/296，完整帧和AI完成均为0。**窗口最长段不是逐帧波形**：某些时刻有72像素输入，不代表最后一次C2帧记录一定包含这些像素。0与72的逐帧差异尚未解释；不能把第二轮的0解释成整轮没有任何DE。

原始证据：logs/c9_stage_min_board_20261103/20261103_160131/result.json、20261103_160412/result.json；独立重放 `tools/report_c9_stage_min_board.py`，汇总logs/c9_stage_min_board_result_20261103.json。重放工具初版因Python整数bank键与JSON字符串键比较误报，已按标准JSON键转换逐字段复核；原报错日志保留，未修改原始采集或降低校验要求。

最后恢复C10，六组静态INT8分数与桌面参考逐项相同：logs/c10_warm_boot_20261101/20261103_160518/attempt.json、reference_check.json。未写Flash、未改DDR参数/校准算法/验收条件，active profile仍display；本轮不是物理冷启动、真实视频/TinyML或HDMI验收通过。

## 下一步的修复边界

先补真实包/行边界及逐帧有效量的证据，区分CSI输出节奏与更前端异常；最近一次WC=2400和VS/HS曾出现不足以证明每个包都完整。随后在CSI与A ISP之间建立有明确valid和行边界语义的RAW10接入层，评估整行双缓冲：完整接收并核对一行后，再连续送出ISP需要的DE。测试须覆盖拍间空隙、PPC尾拍、VS中断、短/长包、溢出和复位恢复；保持坏帧拒绝，按来源保留首像素时间。

当前只完成定位与诊断工具，没有实施该修复。错误debug域仍关闭，CRC/同步健康没有结论；轻量版停用了TinyML，修复后还须回到完整整机重新做DDR/视频/DMA/AI并发验收。
