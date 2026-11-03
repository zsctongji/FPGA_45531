# C7 冷启动异常与隔离修正

当前结论：原 C7 的 Flash 配置完成，但 CPU 读取 Flash 固件时发生串行位错位。C10 已通过完整实现、CPU/DDR/缓存和 ROM 自动读取 Flash 的热启动测试，且已写入 Flash 并完整回读校验；2026-11-01 17:59 的实际断电冷启动也已通过。

## 实板证据

- 冷启动采集：`logs/c7_cold_boot_20261101/20261101_165246/`。记录 USB 断开、COM13 重连，900 秒采集内没有 C1 日志。采集期间没有下载 FPGA 或 CPU 固件。
- 只读配置状态：Ti60 IDCODE `0x10660A79`，USER_MODE、CDONE=1、NSTATUS=1，配置 CRC 错误均为 0。
- 采集结束后才暂停 CPU，PC 为 `0x8`。RAM `[0x1000,0x11000)` 共 65,536 字节，每个字节都等于已烧录 C1 二进制串行左移一位后的结果；仅 5,581 字节偶然与原字节相同。
- 例：预期 `97 81 15 00 93 81 81 77`，实读 `2f 02 2a 01 27 03 02 ee`。
- Flash 原烧录后的完整 8 MiB 回读与保存镜像 SHA256 相同。这一检查只证明存储内容，不证明 CPU SPI 读取或冷启动正确。
- CPU 只读 SPI 探针在模式 0、多个分频下重复得到 JEDEC `DEC02E`，正确器件 ID 应为 `EF6017`。更换 `0B`/`03` 命令、降低分频均未消除异常。

证据索引：`logs/c7_cold_boot_20261101/read_only_device_state.json`、`ram_alignment_analysis.json`、`spi_mode_comparison.json`。原始 Flash 备份和保存镜像仍留在本地 `build/private_*`，不得随交接代码发布。

## 已验证的 RTL 修正

厂家生成 SPI 控制器已经有 `inputPhy_dataReadBuffer`，但接收位选择器的七条输入仍读取原始引脚，而 `readFill/readDone` 已延迟。隔离修正让七条选择器读取已有采样保持寄存器，保持命令时序、SPI 公共接口和软件 ABI。

`tools/test_c7_spi_rx.py` 直接提取实际厂家 SPI 模块：分频 2、8、32 各运行原逻辑和修正逻辑。原逻辑均复现 `DEC02E`，修正逻辑均读出 `EF6017`。报告 `logs/c7_spi_rx_tests.json`。这是仿真证据，仍须实板与冷启动验证。

`tools/prepare_soc_cold.py` 生成 `projects/10_soc_cold`，仅在私有 `overrides/sapphire_soc_spi.v` 应用修正。完整 C7 的 CPU、DDR、C2、C3、摄像头和显示外设均保留。厂家原文件、已验收的 C7/C24 镜像与记录不改动。

## 剩余门槛

1. C10 完整 P&R、主时序、66 位 Gray CDC 和配置镜像身份审计。
2. SRAM 下载 C10 后，由 ROM 自动读取现有 Flash 固件，六组 C1 输出逐项匹配桌面参考；这一实验只算热启动。
3. 通过后再将修正配置写入保存镜像，完整校验 Flash。
4. 用户断开全部供电后重新上电，独立采集自动启动日志。完成此步才可声明冷启动通过。

调试过程中 CPU 一度进入非法代码异常循环；仅写 PC 后不能恢复。OpenOCD `reset halt` 恢复至 ROM `0xf9000000` 后，小型探针正常运行。后续 RAM 诊断加载器在装载前明确复位并暂停 CPU，逐字节回读校验后才恢复执行。

## 修正版已经取得的实板结果

- C10 配置镜像 SHA256：`982ab1bf07f6b8ba825b02c064de014003fc743a08f9083631e5adcc24956f5b`。
- XLR 59,168 / 60,800；RAM 224 / 256；DSP 60 / 160。主时序 setup +0.262 ns、hold +0.026 ns；66 位 Gray CDC 两角检查通过。
- 仅 SRAM 下载 FPGA 配置、没有 JTAG 加载 CPU 固件的自动启动实验：六组 C1 原始 INT8 输出全部匹配桌面参考。证据 `logs/c10_warm_boot_20261101/20261101_173651/`。
- CPU 1 MiB 四模式、字节/半字通道、跨 16/64 字节和缓存失效重填检查全部通过。证据 `logs/ram_diagnostic_20261101/20261101_173856/`。该项不代表外部 DMA 一致性通过。
- 新鲜完整 Flash 备份等于先前校验镜像，再仅覆盖 968,406 字节 FPGA 配置区，其外所有字节和原 C1 固件保持相同。
- 首次厂家校验失败后，工具自动采用最大等待重写并校验成功；独立完整 8 MiB 回读也逐字节相同。最终 Flash SHA256：`76f84fbb41f9e81f06a32c6c9b40976064bdac5e9851a7c51d9c48ea6ac3a59d`。
- 物理断电重启采集已通过：`logs/c7_cold_boot_20261101/20261101_175401/`。记录 USB 断开/重连，六组 C1 输出全部匹配参考，期间未重新下载。

最终结果索引：`logs/c10_board_summary_20261101.json`。CPU/DDR/TinyML 与冷启动已通过；DMA 缓存交接、真实摄像头并发和 HDMI 实际画面不在本报告通过范围。
