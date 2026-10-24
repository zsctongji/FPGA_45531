# C2 第二阶段：厂家接口、APB 与 CPU 接收缓存

日期：2026-10-24。主目录 `C:\Users\16034\Downloads\FPGA\FPGA_2026_T3_P3`。本文件补充并更新 `C2_INTEGRATION.md` 中“厂家接口/APB/缓存尚未实现”的状态。图像 ABI 仍为 v1，新增控制传输 ABI 为 v2。

本轮完成可综合适配器、APB控制服务、RX只读驱动和独立厂家SoC接入副本。真实视频IP、物理引脚/时钟约束、DDR地址别名和板上缓存效果尚未验证。默认没有新的可下载配置或配套CPU BIN；RV32检查只编译对象并检查指令。

## 代码入口与连接

| 文件/目录 | 用途 |
|---|---|
| `projects/06_soc_c2/rtl/c2_axi_to_vendor.sv` | 保留请求ID；串行化写/读通道；窄访问字节通道；地址窗口、重定位和DECERR |
| `projects/06_soc_c2/rtl/c2_apb_control.sv` | 16位字节地址、32位数据的APB3寄存器；命令与完整回复跨域 |
| `projects/06_soc_c2/rtl/c2_vendor_attachment.sv` | 视频适配+整帧写入→厂家互连S1，APB→所有权服务 |
| `projects/06_soc_c2/integration/c2_tinyml_soc_top.v` | 从原TinyML顶层生成的独立接入副本；单DDR，保留CPU/TinyML，视频输入为外部端口 |
| `projects/06_soc_c2/integration/c2_native.xml` | 上述副本的Efinity map工程，没有完整实物约束 |
| `team_work/03_ai_soc/c2/c2_driver.h/.c` | CPU控制、查询/取帧、缓存同步、私有拷贝校验、释放与超时处理 |
| `team_work/03_ai_soc/c2/c2_sapphire.h/.c` | 固定RV32 Sapphire后端：APB MMIO、内存屏障、厂家D-cache失效指令 |

```text
厂家 Sapphire AXI -- CPU ID/窄访问适配 --> 厂家互连 S0 --+
视频 frame_buffer -- 重定位/ID适配 --+                  |
96x96 缩略图 -- CDC/FIFO/写帧 -- C2局部仲裁 --> S1 ------+--> 唯一 DDR 控制器/PHY
厂家 TinyML AXI ---------------------------> S2 --------+

Sapphire APB0 -- APB寄存器 -- 请求/回复CDC -- 双槽所有权服务
```

原顶层的 CPU BID/RID 线没有返回来源，CPU写响应也未接回SoC。本副本在CPU源和S0之间保存原始8位ID，并接回BRESP。厂家互连仍使用自己的ID空间，DDR实例显式配置 `AXI_ID_WIDTH=8`，避免默认4位与互连8位隐式截断。原 `projects/03_tinyml` 没有改写；生成清单及原源码SHA在 `integration/INTEGRATION_MANIFEST.json`。

原APB隐式信号改为明确的PADDR[15:0]、PWDATA/PRDATA[31:0]及握手线。pclk接 `i_peripheralClk`，所有权服务接 `io_memoryClk`，使用完整请求/回复CDC。原系统内存时钟已有 `io_memoryClk=user_clk` 连接，不另造一个同名时钟。

接入副本还显式导出SoC的SPI信号作为逻辑端口，给DDR未提供的QoS输入赋0，并按原TinyML端口保留两位lock宽度。它们没有实体引脚分配，不代表Flash已在实物上连通。

## AXI适配的实际范围

每个适配器最多一个写请求和一个读请求在途，分别保存ID直到B/最后R完成。上游可以反压，响应ID和载荷随有效响应保持。厂家互连内的S0/S2路径没有换成通用仿真仲裁器；`tb_c2_vendor` 中的互连则明确使用行为替身，不能算加密IP功能仿真。

- 128位完整拍、16字节对齐、INCR突发，长度最多256拍且不跨4KiB。
- CPU适配另外允许**单拍**1/2/4/8字节自然对齐访问：下游地址对齐16字节，保留原AXI数据字节通道，并限制WSTRB到允许通道；读返回整128位总线，由CPU按原地址/size选字节。
- 单拍FIXED按同一地址语义处理。窄突发、多拍FIXED、WRAP、非对齐、越页、锁定和窗口外请求均返回DECERR；非法写先排空规定的拍数，再返回错误，禁止它们进入DDR。
- 视频侧允许完整拍，不接受窄访问。输入视频地址从0起、在16MiB预留范围内；下游加候选 `VIDEO_BASE=0x08010000`。A还需核对厂家frame_buffer的地址单位、打包/步长及真实输出属性。
- PROT/CACHE/QOS/REGION不构成一致性或安全隔离；厂家ID-less源端口不提供这些字段。本接入只用于非独占的普通DDR流量，不宣称AXI全功能或缓存一致性互连。

WLAST/RLAST或不合法WSTRB置协议标志；合法事务仍须交完规定拍数。没有失联超时/强制AXI中止。CPU适配错误也送入APB诊断快照。有限背压测试不是吞吐证明，局部仲裁和图像FNV延迟仍需整机帧率/欠载实测。

`c2_map_enable` 必须在共同复位期间固定并在运行期间不变。地址布局、linker排除、实际容量和CPU→DDR转换未验证前保持0；此时视频请求返回DECERR，不授权缩略图写入，驱动初始化拒绝使用。它不是已经核实的板卡设置，更不能把该顶层输入当作已分配的实体引脚。共享候选基址仍为 `0x09010000`，容量64KiB；仿真使用独立小地址图。

## APB寄存器表

现有BSP给APB0窗口为 `IO_APB_SLAVE_0_INPUT=0xf8100000`、长度64KiB；本副本把该端口接给C2。本表是该窗口内的**字节偏移**。更高偏移不镜像，未知地址、未对齐和不允许的写返回PSLVERROR。APB操作在PSEL && PENABLE && PREADY时执行，setup阶段不执行命令。数据写为完整32位，接口没有PSTRB。

| 偏移 | 名称 | 语义 |
|---|---|---|
| 0x00 | ID | 只读0x43325332 |
| 0x04 | VERSION | 只读0x00020000，控制传输ABI版本 |
| 0x08 | STATUS | bit0 BUSY；bit1 DONE；正常值0/1/2 |
| 0x0c | COMMAND | 写触发：bits2:0命令，bit8槽号，其余必须0 |
| 0x10 | GENERATION | 空闲时读写的命令代数暂存 |
| 0x14 | ACK | DONE后写1，释放回复快照；其他写错误 |
| 0x18 | RESPONSE | 只读：bits1:0状态，bit8回复槽号 |
| 0x1c | RESPONSE_GENERATION | 只读回复代数 |
| 0x20 | SLOT_STATES | 回复形成时的两槽状态快照 |
| 0x24 | DROPPED | 回复形成时丢新帧累计快照 |
| 0x28 | PROTOCOL_ERROR | 回复形成时的协议诊断标志快照 |
| 0x2c | MAP_ENABLED | 静态接入允许标志；0时命令拒绝 |
| 0x30/0x34 | SHARED_BASE/BYTES | 静态共享基址/64KiB长度 |
| 0x38/0x3c | VIDEO_BASE/BYTES | 静态视频基址/预留长度 |
| 0x40..0x7c | DESCRIPTOR[0..15] | 16个uint32，顺序与coop_frame_t一致 |

CPU命令只允许QUERY5、ACQUIRE3、RELEASE4。硬件状态返回OK0、BUSY1、ESTATE2、EINVAL3，驱动转换为 `COOP_*` 软件错误码。硬件内部ALLOC/COMMIT/ABORT不能从APB伪造。

操作：确认STATUS=0→写GENERATION→写COMMAND→轮询DONE→读取**同一份**回复/token/描述符→写ACK。BUSY或DONE时不能覆盖暂存/提交新命令。回复在ACK前保持，即使底层槽已改变也不会出现拼接快照；QUERY不保留所有权，ACQUIRE仍要检查generation。SLOT_STATES/DROPPED/PROTOCOL_ERROR是回复快照，不是异步直读的多位总线。

IRQ为DONE电平，在本副本接userInterruptB（BSP PLIC编号17）。当前驱动采用轮询，不启用PLIC，也不改变原TinyML的userInterruptA路径。

共同复位取消APB忙状态、CDC消息和槽所有权；CPU必须同时丢弃旧句柄。不能仅复位APB侧来尝试取消已提交的ACQUIRE。

## CPU缓存处理与使用方法

`c2_poll_copy()` 执行QUERY→ACQUIRE→校验描述符→缓存失效→拷贝9216字节并检查FNV→屏障→RELEASE。私有图像可交给已有C4量化/推理函数；本函数不承担模型推理、帧时间有效期或传感器融合。

```c
c2_io_t io;
c2_sapphire_t platform;
c2_driver_t service;
/* Only after address/alias/linker/board checks have actually passed. */
int rc = c2_sapphire_bind(&io, &platform, IO_APB_SLAVE_0_INPUT,
                          verified_shared_base, mappings_verified);
if (!rc) rc = c2_driver_init(&service, &io, 10000);
if (!rc) rc = c2_poll_copy(&service, slot, private_gray, 9216, &frame);
/* Use private_gray/frame only when rc == COOP_OK. */
```

`mappings_verified=0` 会在访问MMIO前返回ENOTSUP。后端还核对APB读出的共享基址是否匹配绑定地址。私有图像和描述符禁止落在共享区，二者也不得重叠。收到校验/拷贝错误后不能消费输出缓冲。

本轮缓存策略限定为**DMA写入、CPU只读的图像槽**。CPU不在共享槽内量化、不清零、不写描述符；输出写到独立私有数组。两槽起点按64字节缓存行对齐，9216是64的整数倍，不与其他CPU可写对象共用缓存行。

固定Sapphire/VexRiscv后端执行 `fence iorw,iorw; .word 0x0000500f; fence iorw,iorw`，汇编使用volatile及 `memory` clobber。厂家SDK将0x500f定义为整D-cache失效；生成CPU解码命中该指令，并等待DataCache的flush_ready。APB0落在生成CPU的f8000000..f8ffffff IO/cache bypass区。

这不是通用RISC-V CMO或cache clean接口。所核对的DataCache为地址/error/valid标签、存储请求写外存的实现；本轮只使用其厂家失效机制。将来若CPU/DMA双向写共享数据、换核或改为write-back缓存，须重新实现清理/失效策略。C3传感器输出、TinyML其他DMA缓冲不自动获得本策略覆盖。

正常失败（描述符、校验、同步或拷贝失败）会释放已取得的槽。命令超时或总线读写失败使完成状态不确定时，驱动置poisoned并拒绝后续命令；不能盲目重试ACQUIRE/RELEASE。需共同复位硬件、丢弃本地句柄再初始化。轮询预算限定软件读取次数，不提供CPU总线异常的陷阱恢复或外设硬件看门狗。

## 复现与证据边界

根目录 `13_test_c2.cmd` / `python tools/run_c2_selftest.py` 运行34次RTL回归，并构建主机驱动测试、RV32对象和厂家接口核查。报告与逐项日志：

- `logs/c2_selftest.json`、`logs/c2/`：功能仿真及源SHA。
- `logs/c2/vendor_audit.log`、`logs/c2_vendor_audit.json`：APB/缓存/原顶层/接入副本核查。
- `logs/c2/host_driver_test.log`：主机断言、102帧接收（含双槽）及故障路径；缓存是显式的陈旧影子数组模型，断言数以本次日志为准。
- `logs/c2_riscv_compile.json`、`build/c2/riscv/c2_sapphire.asm`：3个RV32对象，检查最终机器指令顺序。
- `tb_c2_cache`：从**原始生成RTL**提取DataCache模块，三次将两路各32组有效标签交给原flusher清除；没有仿真CPU执行指令或实物读回。
- `tb_c2_vendor`：APB控制、完整图像、CPU响应ID、视频重定位并发，保留错误/复位覆盖；厂家互连与DDR用行为模型。

`powershell -NoProfile -ExecutionPolicy Bypass -File tools/run_c2_synthesis.ps1 -Target vendor` 仅综合适配边界。`15_synth_c2_native.cmd` 重新生成独立接入副本并综合真实厂家CPU/TinyML/DDR逻辑；报告 `logs/c2_native_synthesis.json`。map不是Interface Designer、布局布线或板上验证；没有真实摄像头实例、引脚约束和最终运行频率。

本次最终结果：34次RTL运行PASS，主机驱动1923项断言/102帧PASS，3个RV32对象及指令检查PASS；厂家适配边界和native接入副本均Efinity map PASS。native资源为32692 LUT4、29351 FF、49 DSP48；适配边界自身为4515 LUT4、5824 FF、2 DSP48。两份数据包含范围不同，不能相加或作为完整视频整机资源。

native本次保留288条告警，复核快照为 `logs/c2_native_warning_review.json`：新增RTL没有位宽/驱动/锁存器告警，接入顶层余下7项为未使用的原时钟/JTAG端口。原厂家加速器、互连和生成CPU仍有锁存器及未驱动实现网线告警，未宣称已修复；包括CPU fence相关内部信号，故最终机器指令存在也不能单独证明硬件排序/缓存一致性。必须保留指令级或板上DMA陈旧值验证门槛。复核文件绑定本次综合报告SHA，重跑后须按新日志重新核查。

最终仍需：核对容量/地址转换并启用实际映射，A接入完整灰度快照和真实视频AXI，链接调用本驱动的整机CPU程序；随后重做物理时钟/复位/CDC、资源和时序验收，再做板上缓存陈旧值/复用/并发与长期测试。原C1程序仍需真实UART静态推理证据。
