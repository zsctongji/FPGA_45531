# 实物信息与 DDR 时序修正后的电脑端检查

用户于 2026-10-31 反馈“实测电压符合预期”。记录为 `PASS_USER_REPORTED`，接受前述 DDR VDD/VDDQ、VREF/VTT、DDR bank、Flash 供电检查通过的反馈；没有补填具体电压、仪器或测量日志，也没有把它转换为 DDR 校准、读写或冷启动通过。来源与范围见 `logs/hardware_identity_20261031.json`。

U12 标记 D9PTK 经 Micron 官方解码为 MT41K128M16JT-125:K，容量 256 MiB、x16。Micron DDR3L 手册支持 1.5 V 模式；保留本机 DDR SSTL 1.5 V 配置。U14 新照片读为 25Q64JWSIQ，对应 W25Q64JWSSIQ，8 MiB、1.8 V；先前“疑似 256 Mbit”的读图判断已作废，仍需只读 JEDEC/SFDP 佐证。

## 本轮修正与实现结果

原厂家参数 tFAW=35 ns 尚无适用于当前实物的 reduced-tFAW 依据。Micron 标准 x16 时序表列出的 DDR3-800/1066/1333/1600 tFAW 为 50/50/45/40 ns，因此 C7 采用保守的 50 ns。资料是芯片时序依据，P&R 的 setup/hold 正裕量不能替代这个检查。

来源：[Micron 2Gb DDR3 SDRAM 时序表](https://www.datasheets.com/micron/mt41j128m16jt-125-k/datasheet.pdf)、[Micron DDR3L 手册，说明 1.5 V 运行参照对应 DDR3 规格](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/791/MT41K128M16JT_2D00_125M_5F00_K.pdf)。

厂家 DDR 顶层在 SystemVerilog 下将模块体内的时序参数作为 localparam，不能通过实例参数覆盖。C7 因此生成私有 `overrides/ddr3_parameter.vh`，只改 tFAW 为 50000 ps，并复制 DDR 顶层将 include 指向该文件；受保护代码与版权内容保持逐字节一致。工程和 core 都引用私有头文件。原 `projects/03_tinyml`、C6 与 C24 固件输入没有改动，原包 781 项检查仍通过。

本轮重新执行 Interface、map、P&R、主 STA 和独立 CDC skew 检查，未沿用旧布线结果：

| 项目 | 当前结果 |
|---|---|
| CPU/core/APB；DDR CK | 100 MHz；400 MHz |
| 主 STA | 29 组 setup、29 组 hold 均非负；最差 +0.119 ns / +0.026 ns |
| Gray CDC | 10 组、66 位两角均有实际路径；最大 skew setup 0.047 ns、hold 0.026 ns |
| 打包资源 | XLR 58,702 / 60,800（96.55%）；Memory Blocks 224/256；DSP 60/160 |
| 综合原语 | LUT4 36,879；FF 30,452；RAM10 220；DSP48 55；ADD 7,264 |
| 物理参考审计 | 544 项通过；新增私有 DDR 头文件、参数和受保护载荷身份检查 |
| 功能回归适用范围 | 原 58 项像素/ISP/C2 RTL 用例的实际输入文件哈希仍一致，本轮复核其身份；未重复执行，也不声称覆盖厂家加密 DDR 调度 |

旧 35 ns 版本的配置与报告保存在本机 `build/physical_20261031/pre_ddr_tfaw50/`。早先 225→100 MHz 的 netlist 复用日志只用于历史追溯；当前版本经过重新综合。

## Flash 静态布局

新增离线 `pgm` 流用于 LBF→配置文件转换。Efinity 的 USB `program` 流没有开放到此脚本；未连接下载器或板卡。配置文件在 `projects/07_soc_physical/outflow/`，仅为待板上验证的构建产物，不是已验收发布包。

`soc_physical.hex` 为 Efinity 的每行一个字节的十六进制流，不是 CPU Intel HEX。校验全部行格式、生成记录、源 routed LBF 和当前 STA 审计身份后计得 948,550 字节；连容器信息一并计入，作为配置占用的保守上界，不使用 ASCII 文本文件大小判断 Flash 地址。

| 区域 | 地址/大小 |
|---|---|
| Flash 总容量 | 0x800000 字节（8 MiB） |
| FPGA 可用预留区 | [0, 0x380000)；配置流保守上界 948,550 字节，静态不越界 |
| CPU 固件起点 | 0x380000 |
| 当前 C24 原始 BIN | 1,393,872 字节；末端 0x4D44D0，不含调试信息或 HEX 文本膨胀 |
| ROM 固定读取区 | [0x380000, 0x780000)，4 MiB；在 Flash 容量内 |
| RAM 复制区 | [0x1000, 0x401000) |

审计从四个 ROM lane 重组 4096 字节，确认其 664 字节有效引导程序与原交叉编译 SHA256 一致，其余为零填充；C24 BIN 与已链接产物哈希一致。引导程序选择单数据线 SPI，读指令 0x0B、三字节地址和一个 dummy 字节。具体 SPI 外部时序、器件响应、最终下载工具的地址解释、写后读回与上电启动仍待验证。

## 复现与剩余验收

- `26_build_soc_physical.cmd`：准备 C7、执行功能回归、综合/P&R、STA/CDC 和物理参考审计。
- `27_prepare_board_review.cmd`：先核对现有实现，再仅在电脑生成配置文件并运行 `check_board_preflight.py`；46 项静态检查通过，发布状态仍为 REVIEW_REQUIRED。
- 当前报告：`logs/soc_physical_audit.json`、`logs/soc_physical_pgm_check.json`、`logs/board_preflight_20261031.json`；便于审阅的实现报告副本在 `logs/soc_physical_evidence/`。

下一步在板上先确认 DDR calibration 完成，再以独立诊断程序运行地址别名、固定图案、伪随机读写及重复冷启动；测试区须避开运行代码、栈和帧缓存。另需完成 Flash JEDEC/SFDP、写后读回、真实相机/FPC 与蜂鸣器极性核对。厂家受保护控制器的完整调度/MRS、温度刷新、物理带宽和整机 CPU/AI 运行尚未验收。不得仅凭供电和离线检查通过启用 live map 或宣布整机通过。
