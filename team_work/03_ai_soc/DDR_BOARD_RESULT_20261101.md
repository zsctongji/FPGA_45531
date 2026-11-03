# 2026-11-01 独立 DDR 实板结果

结论：C8 独立 DDR 诊断的首次 JTAG 配置、KEY0 复位重测，以及用户确认重新上电后再次 JTAG 配置三次均通过。实际两个 PLL 锁定、DDR 校准完成，256 MiB 全容量测试完成；不代表 C7 CPU/AI/视频整机或 Flash 自动冷启动已经通过。汇总证据见 `logs/ddr_board_20261101/summary.json`。

## 本次身份与连接

- 尝试目录：`logs/ddr_board_20261101/20261101_121928/`。
- 时间：2026-11-01 12:19:28 至 12:20:02，UTC+08:00；主机从启动下载到采集结束约 31.25 秒，包含下载和两条终态记录等待，不作为 DDR 带宽指标。
- 本会话用户提供的 Ti60F225 主板；U12 标记 3HK77 / D9PTK，对应 MT41K128M16JT-125:K，256 MiB。硬件照片和用户电压反馈背景见 `logs/hardware_identity_20261031.json`；本次未测量新的电压值。
- FT4232HL，VID:PID `0403:6011`，无唯一 USB 序列号；JTAG ID 实读 `0x10660A79`。该 ID 确认器件类型，不提供板卡唯一身份。
- B/MI_01：用户安装 libusbK，Efinity 标准后端识别成功。C/MI_02：UART COM13，FTDI 驱动保留。115200、8N1、无流控，DTR/RTS=false，没有发送串口命令。
- 工具 Efinity 2026.1.132，JTAG 1 MHz，实际 URL `ftdi://0x0403:0x6011:0:ff/1`。仅执行 `-m jtag`，未执行 Flash 擦除/写入。
- 镜像：`fpga_bitstreams/ddr_diag_100mhz/ddr_diag.bit`。
- 镜像 SHA256：`752d7855d7726ec61fdc1b863df381ff7fdac0f6577f0f59eeb8af812f9a6add`。

## 实测内容

诊断采用 DDR CK 400 MHz、AXI/core 100 MHz、1.5 V SSTL 和 tFAW 50 ns。先核对 0 地址及 bit4 至 bit27 的地址别名探测点，再对 [0, 0x10000000) 完成全零、全一、地址相关、混合地址相关四轮全写后全读，每项核对 128 bit 数据。

串口共记录 23 条完整状态，从复位进入测试，再连续收到两条：

```text
DDR|S=06 L=3 C=1 I=16 E=00 A=00000000 N=04000019 P=00000000
```

L=3：两个 PLL 锁定；C=1：校准完成；E=00：未报错；N=0x04000019：核对 67,108,889 个 word。程序退出码 0，`tools/check_ddr_uart.py` 给出 PASS_LOG，2 条完整容量 PASS，问题列表为空。本次只记录到复位、测试和通过状态，未捕获校准等待的中间过程，不能据此测量校准耗时。

## 原始证据

所有相对路径均以本工程根目录为基准。

| 文件 | 用途 |
|---|---|
| `logs/ddr_board_20261101/20261101_121928/attempt.json` | 下载参数、实际镜像 SHA256、设备扫描、返回码、时间及日志 SHA256 |
| `logs/ddr_board_20261101/20261101_121928/jtag_scan.log` | 本次下载前重新扫描到的器件 ID |
| `logs/ddr_board_20261101/20261101_121928/programmer.log` | 厂家程序实际下载完成记录 |
| `logs/ddr_board_20261101/20261101_121928/uart.log` | 原始串口字节记录 |
| `logs/ddr_board_20261101/20261101_121928/uart_check.json` | 原始串口解析及通过判据 |
| `logs/ddr_board_20261101/20261101_121928/usb_devices.json` | 下载后 PnP 接口和驱动状态快照 |

UART 日志 SHA256：`757ca6709e268f8d1db81acb53fed00c201f17127a99faeebe0258442792d971`。

## KEY0 重测：已通过

2026-11-01 12:24:04 至 12:25:09，COM13 持续采集期间，用户再次按 KEY0/SW0。本次没有重新配置 FPGA，也没有访问 Flash。已实际捕获 `S=00 L=0 C=0 N=00000000` 复位状态、重新进入 `S=03 L=3 C=1` 的读写过程和连续两条完整 PASS。该次日志共 26 条记录，检查计数仍为 `N=04000019`，E=00，无解析错误。

证据目录：`logs/ddr_board_20261101/key0_20261101_122404/`，包含 `attempt.json`、`uart.log`、`uart_check.json` 和本次只读串口采集脚本。开启采集后、再次按键前收到的已有 PASS 单独保存在 `pretrigger_uart.log`，没有混入本次验收日志；因此本结论来自观察到的新复位及完整重测过程。配置身份关联首次 JTAG 尝试及未变化的本地镜像 SHA256，本次未独立回读硬件镜像身份。

KEY0 重测 UART SHA256：`164a91882145eb21a043fda5a44efc85c7dd543ba2833850fa8a3d489feec8ff`。

## 重新上电后 JTAG 测试：已通过

用户确认已断开全部供电并重新上电；本机未独立测量断电时长或电源轨。最初连接到了电脑 USB(5)，Windows 将 B/MI_01 绑定到 FTDIBUS，UART 为 COM16，Efinity 标准后端找不到下载器，此时未下载镜像。用户插回原电脑 USB(1) 后，B/MI_01 的 libusbK 及 C/MI_02 的 COM13 恢复，再开始本次实际测试。

2026-11-01 12:28:13 至 12:28:45，先打开 UART，再以同一 SHA256 镜像、1 MHz JTAG 重新配置 SRAM。JTAG ID 再次实读为 `0x10660A79`，厂家下载程序返回 0。串口捕获复位、测试及连续两条 PASS，共 23 条记录；`S=06 L=3 C=1 I=16 E=00 A=00000000 N=04000019 P=00000000`，解析结果 PASS_LOG，无错误。下载及采集总计约 30.516 秒，不作为校准耗时或带宽测量。

证据目录：`logs/ddr_board_20261101/cold_20261101_122813/`，包含 `attempt.json`、`jtag_scan.log`、`programmer.log`、`uart.log`、`uart_check.json`、`usb_devices.json` 和采集脚本。

本次 UART SHA256：`4ce1cd2645a102897e77c4855837343cf73fede31f41a590db2cce43cecc017c`。

本结论范围是“用户确认重新上电后，重新 JTAG 配置并完成 DDR 测试”。没有执行 Flash 擦写，也没有验收 Flash 自动启动。

## 后续验收

1. KEY0/SW0 复位后的完整重测已通过；不要用 CRESET_N 代替，它可能返回旧 Flash 配置。
2. 用户确认重新上电后的 USB 识别、重新 JTAG 配置及完整 DDR 测试已通过；临时配置断电消失，此步骤仍不等于 Flash 自动启动。
3. 在 C7 整机中分别验收 CPU 启动、DDR/缓存、TinyML 与视频/传感器并发。本次没有运行这些功能，也未读取 Flash JEDEC/SFDP。

原始离线 BUILD_RECORD.json 及 2026-10-31 硬件接收记录保留其历史状态；本次硬件通过证据独立保存，不据此开放整机物理发布。
