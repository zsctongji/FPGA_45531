# C7 CPU、DDR/缓存与 TinyML 实板验收（2026-11-01）

本轮使用 C7 整机顶层、100 MHz CPU/core/APB、400 MHz DDR；KEY3 保持默认释放，实时视频/传感器映射关闭。全部加载使用 JTAG 临时配置 FPGA SRAM、调试器写入 DDR，不执行 Flash 擦写。独立 C8 的三次通过记录仍保留，不能直接替代 C7 整机测试。

**结果：已通过 C7 CPU 启动、CPU 侧 DDR/缓存基础检查及六张静态样图 TinyML 实板验收。** 六张图的原始 INT8 分数与已有桌面参考逐项完全一致。C2 外部 DMA 制造 stale-cache 的负例、真实视频/传感器并发及 C7 冷上电/Flash 自动启动仍未完成，不开放整机物理发布。

| 项目 | 本次实测结果 |
|---|---|
| 修正后 FPGA 镜像 SHA256 | `dd49ca7f8064a70e52ff1370646e6858c20d6d659249b8b00c126f95e7d33411` |
| 重新综合、P&R、STA/CDC | 29 组 setup / 29 组 hold 非负，最差 +0.270 ns / +0.023 ns；66 位 Gray CDC 两角通过；552 项参考审计、47 项静态检查通过 |
| 实际资源 | XLR 58,926/60,800（96.92%），Memory Blocks 224/256，DSP Blocks 60/160 |
| CPU 诊断 | 固件完整 DDR 读回 SHA256 相等；APB ID/ABI/map/error、公共时间、四图案读写及 byte/halfword lanes 全部通过 |
| CPU DDR 检查范围 | 四个 256 KiB 区，共 1 MiB；四图案核对 1,048,576 个 32-bit word；含全 D-cache invalidate 后读取 |
| 原实板故障复现命令 | 同一 `probe_c7_ddr.py` 在修正前 FAIL，修正后 bulk/word/byte 三种写入均 PASS |
| C1 固件 | 原封不动的 `c1-02a568e5375cc27b`，1,416,824 字节 BIN 完整读回 SHA256 相等后执行；入口 0x1000 |
| C1 日志与参考比较 | BOOT/MODEL/六次 Invoke/DONE 完整；6/6 静态标签符合预期，六组 person/no_person INT8 分数差均为 0 |

CPU 诊断尝试：`logs/c7_board_20261101/cpu_diag_20261101_125916/`（12:59:16 至 12:59:34，UTC+08:00）。C1 尝试：`logs/c7_board_20261101/c1_20261101_125949/`（12:59:49 至 13:03:26，包含约 65 秒下载、150 秒完整读回和程序运行）。实板原始 UART、配置/固件身份、加载命令、读回文件及解析结果各自保存；汇总见 `logs/c7_board_20261101/summary.json`。JTAG 使用 FT4232HL B/MI_01，实读 Ti60 ID `0x10660A79`；UART C/MI_02=COM13、115200/8N1、DTR/RTS=false。

| 静态样本 | person INT8 | no_person INT8 | 与桌面参考差异 | Invoke 实测 ms |
|---|---:|---:|---|---:|
| person | 113 | -113 | 0 / 0 | 249.713 |
| no_person | -57 | 57 | 0 / 0 | 249.601 |
| people1 | 93 | -93 | 0 / 0 | 249.656 |
| people2 | 57 | -57 | 0 / 0 | 250.201 |
| no_people1 | -51 | 51 | 0 / 0 | 250.253 |
| no_people2 | -111 | 111 | 0 / 0 | 250.065 |

Invoke 时间以 100 MHz CLINT ticks 计算，均值约 249.915 ms。现有固件仍输出层级 profiler 日志，该时间包含这些日志及软件开销，不作为无日志纯算力或摄像头帧率。桌面参考使用已经审计的 bias quantized_dimension 元数据兼容副本（原模型 SHA `808cfdfc…`，桌面副本 SHA `77cac99d…`），板上使用原模型；没有通过改模型、输入或标签来获得本次通过结果。六张静态图不代表数据集准确率。

## 已发现的 CPU 字节通道问题

原 C7 镜像 SHA256 为 `962079f839a2f0348142e87fd83dd841f1534e30de42d71f5edb6de52d1ea26b`。配置成功且 CPU 被 JTAG 正常识别，但 1,416,824 字节 C1 固件完整读回有 915,770 字节不一致，每个 16 字节块只有前 4 字节正确；尚未执行该固件。完整错误读回、下载和校验记录位于 `logs/c7_board_20261101/c1_20261101_123527/`、`c1_verified_20261101_123723/`。

最小实板复现命令为 `python tools/probe_c7_ddr.py`。向 0x02000000 写入 16 字节 `0102030405060708090a0b0c0d0e0f10`，实际读回 `01020304000000000000000000000000`；重复运行及逐字写入均复现，日志分别归档。该命令要求板上已加载 C7，CPU 将被暂停，测试会覆盖该 16 字节。

根因是厂家生成的 `BmbUpSizerBridge` 保留 CPU 原始字节地址，`BmbToAxi4Bridge` 统一声明 SIZE=4，该地址规则与 C7 原适配器仅接受 16 字节对齐整拍的规则不匹配；对偏移 4/8/12 的单拍字写入，原适配器返回 DECERR。新模块 `rtl/c7_cpu_axi_address.sv` 只在 C7 CPU 边界将 SIZE=4、LEN=0 的地址向下对齐 16 字节，保留已移位 WDATA/WSTRB 和整拍读返回；burst 和其他请求继续原有校验。没有修改厂家生成源码、加密 DDR 控制器或 C6 通用适配器。

`tools/test_c7_cpu_lanes.py` 实际提取并编译当前厂家 BMB upsizer，接固定 SIZE=4 的桥边界、C7 归一化模块、原 C2 适配器与内存夹具。原直连负例稳定在 offset=4 返回 DECERR；归一化后 28 次 store、48 次 read 通过，覆盖所有 16 个偏移、字节/半字/字及读背压。报告 `logs/c7_cpu_lanes_tests.json` 绑定实际源文件哈希，整机构建入口和物理审计已包含该检查。修正前实现及报告保存在本机 `build/c7_board_20261101/before_cpu_lane_fix/`。

本轮已完成 RTL 修正、负例/正例回归、重新综合/P&R与修正后实板验收，结果见上表。原失败记录保留，不与新尝试合并或改写成 PASS。

## CPU DDR/缓存专用固件

源码 `team_work/03_ai_soc/c7_board/`，构建 `python tools/build_c7_board_diag.py`，输出 `firmware/c7_board_diag/`。固件入口 0x01000000，栈顶 0x01010000，独立 64 KiB 链接区；不会覆盖原 C1 应用或测试数据。

测试区是 0x02000000、0x04000000、0x06000000、0x07000000，各 256 KiB，共 1 MiB；**会覆盖这些区域的数据**。四图案全写后全读，共核对 1,048,576 个 32-bit word。每轮读取前执行当前 VexRiscv 的全 D-cache invalidate 指令 0x0000500f 及内存屏障，覆盖缓存容量以外的实际 DDR 重读。另检查字节/半字 WSTRB、16/64 字节边界、C2 APB 身份/禁用映射/错误状态及 CLINT 与公共 APB 时间的 100 ms 增量。

这验证 CPU 访问、失效指令和 refill；没有硬件外部写入者制造 stale-cache 负例，不宣称 C2 DMA→CPU 一致性已通过。

## JTAG 实板执行入口

需先完成新 C7 map/P&R、主 STA/CDC、pgm 和 `python tools/audit_soc_physical.py`。使用 Efinity 自带 Python，以获得项目已有的 pyserial：

```powershell
$env:PYTHONHOME = "$PWD/tools/efinity/2026.1/python311"
& "$env:PYTHONHOME/bin/python.exe" tools/run_c7_board_acceptance.py --stage cpu_diag --configure
```

脚本核对当前 HDL/约束/布线、离线审计及固件哈希；先打开 COM13，再仅执行 JTAG SRAM 配置。CPU 固件加载后完整 dump 到电脑并核对 SHA256，相等才执行入口地址。当前 OpenOCD 的 VexRiscv 目标没有 `checksum_memory`，因此不用 `verify_image` 作为验收方法。UART 为 115200/8N1，无流控，DTR/RTS=false，不发送命令。

CPU 诊断通过后，可关联本次配置尝试运行原 C1 六图固件，不必重新配置 FPGA：

```powershell
& "$env:PYTHONHOME/bin/python.exe" tools/run_c7_board_acceptance.py --stage c1 --configuration-attempt "logs/c7_board_20261101/cpu_diag_实际时间/attempt.json"
```

每次尝试独立保存在 `logs/c7_board_20261101/`，包含加载参数、配置/固件 SHA256、完整读回、OpenOCD 日志、原始 UART 及解析结果。CPU 诊断用 `check_c7_board_uart.py`；C1 用原 `check_c1_uart.py`。后续与 `logs/pc_ai/c1_reference.json` 比较六张样本的原始 int8 分数，参考模型为已经审计的桌面元数据兼容副本，板上仍使用原模型。

## 验收范围

当前实物 USB 连接须沿用已安装 libusbK 的电脑 USB 口：B/MI_01=JTAG，C/MI_02=COM13。换电脑 USB 口后可能重新绑定 FTDI，需要重新识别，不能直接复用旧 URL/COM 号。

完成本轮 CPU 与静态 TinyML 后，真实视频写入/显示、AI 缩略图搬运、CPU 缓存交接及真实传感器并发仍须各自验收。Flash JEDEC/SFDP、写后读回和 Flash 自动冷启动也不在本次 JTAG 执行范围内；整机物理发布保持关闭。
