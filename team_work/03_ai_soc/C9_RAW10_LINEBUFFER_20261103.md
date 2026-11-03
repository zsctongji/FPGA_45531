# RAW10整行缓存修复候选（2026-11-03）

基于两轮分级板测的18×4PPC→36×2PPC→72×1PPC碎段证据，修复CSI到A ISP之间对DE的解释。DDR参数、校准算法、引脚、PLL和验收条件不变；新实验独立于已冻结的stage_min及C10，正式active profile不变。

厂家 [MIPI 2.5G CSI-2 RX UG v2.7](https://www.efinixinc.com/docs/mipi-2-5g-csi2-rx-core-ug-v2.7.pdf) 的Generic时序说明：HS随有效数据变化，不能当独立行尾；pixel_line_num来自行短包，不能假定Generic输入提供逐行编号。文档也说明像素时钟偏高可能使一行内pixel_data_valid间歇。因此当前72像素碎段不是足够的摄像头硬件故障证据。

本轮检验三个可区分条件：有效负载完整但间歇时，应恢复完整行；负载量/字节数/PPC错误时，应拒绝完成坏帧；收到传输错误时，即使计数正确也必须停止发布。不能把前一种的缓存恢复用于掩盖后两种错误。

## 实现与边界

源码c9_live/camera_geometry/c9_raw10_linebuffer.sv。在原生50 MHz像素域先收齐一行，再以连续4PPC输出，之后仍走原RAW拆分、A ISP、灰度转换、1PPC拆分与C2。两个RAM银行分别由写入或读出占有，尚未读完的银行不允许覆盖；RAM不复位，所有权/ready复位后避免读到陈旧数据。

本版固定RAW10、VC0、1920×1080、WC2400、每个有效拍PPC4；每行480拍，整帧518400拍。允许有效拍之间有间隙，不把HS或valid下降沿算成行尾。只在自然VS上升沿后开始接收，RUN中途启动时跳过残帧。整个预期宽度收齐才释放一行，保持原像素次序，既不填充、复制也不插入伪像素。各行之间留空白，VS标记待前一帧旧行排出后发送，标记前留32个像素域周期的错误传播等待。

在下一次自然VS检查前帧行数、列余数和总有效拍数；短/长帧均置错。WC、类型/VC或PPC不符、双缓冲占用冲突、未完成行停顿超过50000周期（1 ms）、VS碰撞/排队过深或传输错误，也置粘滞错误并停止未来输出。C9源选择只提交一次，正常清除这些错误仍需公共复位。已经送出的部分行不会靠生成一个伪造关闭VS变成完整帧。

这是按固定格式字节数/整帧总量建立的行接入层，不是独立CSI包解析器。若上游静默丢失并补偿同等数据、且没有任何错误指示，本模块不能凭总数证明每个包/像素正确。严格拒绝坏包还依赖厂家CRC/ECC/undersize/FIFO等错误通路；完整数据内容与AI效果仍须另验。

## 传输错误与时钟域

原厂家AXI/debug时钟和复位固定零。本候选接到原生像素时钟/复位，保持AXI读写请求关闭，但让debug实际工作。错误门要求init_done，并采样0x0007447d掩码（原0x447d加lane0 SoT/Control/Escape错误），FIFO empty不作硬错误；空FIFO造成的valid间歇由缓存承接。init_done缺失也阻止输出。厂家IP及PACK_TYPE=1、tINIT、FRAME_MODE参数均不改。

PHY bank4改为原生域原子64位观测：63:56标记F1；55 RUN同步态、54已在自然VS启用、53格式器fault、52:46七项错误（低到高：银行溢出、metadata、PPC、帧负载/边界、transport、VS排队、部分行超时）；45:27最近结束帧的有效拍数；26:25输入帧计数模4；24:0 RUN后debug各位出现集合。模4值不能作为精确帧总量，debug集合不表明各位在同一时刻出现。

ISP bank仍由pixel2_clk获取，视频word6仍保留原video时钟域pixel/source最长有效段。首版曾把native计数直接接到video快照，审查时发现后已停止并保留源码/日志，未加载板卡；v2使用各自时钟域的既有快照，不混读多位总线。初版记录logs/c9_linebuffer_initial_stopped_20261103.json。

C2的毫秒时间仍在首个输出GRAY8 DE锁存；加入行缓存会增加像素路径延迟，不能把该时间当原始CSI首拍到达时间。物理CSI时间到统一时间的额外标定/元数据转发属于后续整机同步验收。

## 回归与入口

tools/test_c9_linebuffer.py共20项：原链路带间隙仍宽72的失败用例；连续/间歇输入在三个相位下经实际A ISP恢复1920完整行与3帧；后级valid/门控隔离；逐词次序、WC/PPC/VC错误、短/长帧、超时、缓冲溢出、传输错、复位与RUN中途启动。没有模拟加密CSI核。另有10项几何负例和5项协议负例，确保CRC或坏计数不能获得几何通过。报告logs/c9_linebuffer_tests_20261103.json、logs/c9_linebuffer_decode_tests_20261103.json。

候选工程build/c9_linebuffer_v2_image_20261103继承轻量stage_min，CPU/C2/唯一DDR和视频保留，TinyML加速器仍停用。生成prepare_c9_linebuffer.py，编译run_c9_linebuffer.ps1，审计audit_c9_linebuffer.py，打包report_c9_linebuffer.py；run_c9_linebuffer.py默认仅离线核对，显式--capture才加载/采集，finally恢复C10，未包含Flash写入。check_c9_linebuffer.py只报告独立geometry_verified，不授予真实AI/HDMI/冷启动或整机并发通过。

物理与实板结果应以独立审计及采集记录为准，以上仿真通过不能代替真实摄像头验收。

## v2物理与首次板测

v2通过物理审计：31471 XLR，setup +0.384 ns、hold +0.026 ns，66位Gray CDC双角通过；位流SHA256 f0c9dca964ffcd3e8209346d9a52c04ecc5efd8677d92ec86b475cd2744994c9。首次采集logs/c9_linebuffer_board_20261103/20261103_164726/result.json，校准与3508字节固件完整回读通过，但几何未通过：格式器尚未在自然VS启用就因transport置错，输出帧数为0。

RUN后debug集合0x0029c41a，掩码内0x00014418，记录到ECC1/ECC2、VC0帧同步、receive及lane0 SoT等位；init_done也出现。集合没有发生时刻，不能判断各位同时出现或持续发生。由于原AXI请求始终关闭，本次未清除历史ISR，尚不能把这些位认定为持续活动故障，也不能把它们忽略后宣称好帧。最后已恢复C10，六组静态推理通过，记录logs/c10_warm_boot_20261101/20261103_164833/attempt.json。未写Flash。

## CSR启动资格版本

新增c9_csi_capture_gate.sv和独立linebuffer_csr工程。流程为等待init_done、读取旧ISR、分别握手AW/W写0x7ffc清除ISR[14:2]、等写应答、读取ISR确认错误清除，之后才允许格式器等待自然VS。持续错误最多重试8次，总超时20 ms；无法清除或总线超时均不开始接收。FIFO empty仍不作硬错误；FIFO full和ISR错误位仍阻止开始。

接收后不再自动清除ISR，新错误继续触发原掩码的粘滞拒绝。格式器不对其尚未接收的RUN中途残帧置transport错；在自然VS启用后，新传输错误仍立即停止未来发布。独立c9_raw10_linebuffer_csr.sv与原v2源码仅模块名和这项pre-arm条件不同，未改RAM、像素、行数、总量或丢帧门限。

CSR版本将原camera bank改为原生像素时钟域160位记录：word0标记C9F20001，word1旧ISR，word2清除后ISR，word3清除前debug，word4高8位state、接着8位retries、低4位fault/capture_enable/init_seen/RUN；其他位保留零。PHY仍F1，但debug集合只在格式器自然VS启用后累积；video word6仍为video域最长段。没有把native状态当ISP域数据采样。该版不再提供ISP内部最长段，不能编造其值；完整C2几何、pixel/source最长段及聚合fault门控另行核对。

16项门控/缓存测试（AW或W先握手、W1C/回读、持续错误、应答/初始化超时、旧错误在pre-arm时跳过、启用后的新错拒绝、原像素顺序/短长帧等）通过；另4项经实际A ISP的连续/间歇输入与两个相位通过。解码资格负例确保旧ISR可以在清除确认后保留作证据，但新CRC、清除失败、坏负载/帧形状不能获得geometry_verified。报告logs/c9_linebuffer_csr_tests_20261103.json、logs/c9_linebuffer_csr_chain_tests_20261103.json、logs/c9_linebuffer_csr_decode_tests_20261103.json。

入口分别为prepare_c9_linebuffer_csr.py、run_c9_linebuffer_csr.ps1、audit_c9_linebuffer_csr.py、report_c9_linebuffer_csr.py、run_c9_linebuffer_csr.py；check_c9_linebuffer_csr.py绑定独立variant。仍是无TinyML的隔离诊断，默认离线、显式capture才接板，finally恢复C10。

## 后续对照及当前结论（18:21）

六个候选均为独立工程、位流、审计和日志，未覆盖已资格通过的构建。CSR版两轮虽然完成启动清除，但没有取得完整帧；随后加原生VS边沿观测，确认接收器实际有自然帧事件和RAW10 VC0、PPC4、WC2400输入。整行缓存后的video pixel/source最长连续段已达到1920；最长段只证明出现过完整宽度的连续输出，不能证明1080行完整帧。

| 候选 | 单独变化 | 板测目录时间 | 结果 |
| --- | --- | --- | --- |
| linebuffer_csr | 启动W1C及回读资格 | 170717、171213 | 启动资格完成，未取得输出完整帧 |
| linebuffer_edges | 原生VS边沿及元数据观测 | 172725 | VS上/下沿244/244，最大宽1920，transport拒绝 |
| linebuffer_reset | 摄像头GPIO与I2C延时复位对齐现有camera_reset_n | 174812 | VS246/246，最大宽1920，仍记录ECC/帧同步/SoT错误 |
| linebuffer_stream | 配置/读回完成并经CSR资格后才写stream-on | 175918 | 最大宽1920；本次未记录CRC/ECC/帧同步错误，但记录新的SoT状态，整帧拒绝 |
| linebuffer_quality | 自然VS启用后等待32个连续PHY干净周期再允许输出 | 181949 | 资格释放后仍出现SoT错误，粘滞拒绝；完整帧未通过 |

目录前缀分别为logs/c9_<候选名去掉linebuffer前缀后的对应名字>_board_20261103；精确路径由logs/c9_linebuffer_work_checkpoint_20261103.json及各board_result报告记录。每次诊断均检查DDR校准、3508字节CPU固件完整回读，并在finally恢复C10；没有写Flash。

复位对齐保持原极性及13位延时计数（819微秒）；未改DDR复位、时序或校准。stream版本通过公开补丁工具patch_c9_camera_stream_gate.py在本地厂家明文I2C控制源码生成独立副本：原早期0x0100=1改为standby，配置及16次读回后追加一次0x0100=1，且等待经两级同步的接收启动资格。厂家完整RTL不随交接目录上传。

quality版新增c9_receiver_quality.sv及独立缓存变体。旧PHY错误是否只是停钟后保持的状态仍是待证假设，不能靠删除错误掩码宣布正常。该版保留启动资格前PHY状态，要求启用后连续32个原生50MHz周期无SoT/Control/Escape错误；资格后任何新PHY错误均粘滞致命，CRC/ECC/FIFO/初始化和原帧数量检查始终生效。持续坏PHY时绝不释放VS或像素，缓存占满也按错拒绝。

最新板测181949中，pre/post ISR均0x2（仅FIFO empty），质量资格已释放，prequalification_error=false，但active_error=true。debug集合0x00298002含SoT位16；未记录SoT与native DE同周期出现。该观测证明资格之后采到了错误状态，不能确定其物理发生时刻、具体包或根因，更不能由不与DE重合推断该错误无害。normalizer armed=true、fault=0x10、last_frame_beats=0，C2无完整1920×1080记录，source_frames=1、format_errors=0，故geometry_verified=false。

最新质量位流SHA256为5fb524c4063a6074157bfe8d602754f8f39b902b0106bb674ab364fe78c4c5ba，审计SHA256为4e0b6af2a87e3f4a80ebcb7f760e407a42bd0922ed9f7c8db6e3381c361f5cfe；31265 XLR，setup/hold +0.362/+0.026 ns，66位Gray CDC双角通过。14项质量门/缓存测试、4项真实A ISP链路仿真和17项解码负例通过，均不模拟加密CSI核。板测原始证据离线重放入口：tools/report_c9_linebuffer_quality_board.py。

最后恢复C10：logs/c10_warm_boot_20261101/20261103_182056/attempt.json，六组静态推理通过。本轮没有真实视频TinyML、显示器输出、整机并发或物理冷启动验收；active profile仍为display。

## 下一步排查顺序

1. 排线接触/连接不稳定：若是原因，完全断电后重插两端并保持原朝向，用同一质量位流复测应使新SoT错误消失。当前已请求实际排线检查，电脑无法代做。
2. 摄像头发射时钟/时序与实际接收PHY配置不匹配：若是原因，排线复测后错误仍可重现；需拿实际模组及本PCB的厂家可用参考配置核对，不能凭商品芯片名改lane映射或速率。
3. SoT调试信号在停钟/事务边界上的保持或采样语义：若是原因，应以字节域有时钟时的事件记录及官方接口解释区分；当前像素域采样尚不能证明。未获证据前继续拒绝，不屏蔽错误。

先保持位流、固件、摄像头配置及验收门限不变，物理操作后复测，以免混淆变量。通过完整帧后再恢复TinyML资源并做DMA缓存交接、真实视频并发与冷启动。
