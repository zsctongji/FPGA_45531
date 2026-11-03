# C7 完整 SoC：SPI 接收修正版（C10）

2026-11-01 实板结果：CPU 启动、DDR/缓存、六组静态 TinyML 和 Flash 自动冷启动均通过。DMA 缓存交接、真实视频并发、传感器联动和 HDMI 实际画面仍须分别验收。

- 配置镜像 `soc_physical.bit` SHA256：`982ab1bf07f6b8ba825b02c064de014003fc743a08f9083631e5adcc24956f5b`。
- 完整 C7 外设保留，仅通过私有 override 修正厂家 SPI 引脚采样与延迟接收选通信号错位。
- CPU/APB 100 MHz、DDR 400 MHz。XLR 59,168 / 60,800，RAM 224 / 256，DSP 60 / 160。
- 主时序 setup +0.262 ns、hold +0.026 ns；66 位 Gray CDC 双角检查通过。
- 17:59 冷启动记录包含 USB 断开与重连，期间未下载 FPGA/CPU，六组原始 INT8 输出全部匹配桌面参考。

证据入口：`logs/c10_board_summary_20261101.json`，详细说明 `team_work/03_ai_soc/C7_COLD_BOOT_DEBUG_20261101.md`。

本机 Flash 已保存本配置及原 C1 固件；CPU 固件仍从 `0x380000` 读取，内容 SHA256 为 `73401bb622454d06fd9fdc57ea799a0191cbd852574ccec9442f19006346307e`。

这里的 `.hex` 是 FPGA 配置字节流，不包含完整 8 MiB Flash 保存镜像。完整保存镜像混有板卡先前的未知内容，只保留在本机私有备份中，不随交接发布。重新部署必须按保留式烧录流程备份、合并和完整校验。

复现工程由 `tools/prepare_soc_cold.py` 从已验收 C7 与本地厂家 SDK 生成。原厂家 RTL 和原 C7 镜像保持不变。
