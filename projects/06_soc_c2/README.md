# C2：共享 DDR 功能边界与离线验证

当前native输入已从网格样本改为源像素GRAY8/VS/DE，实例化A采样器并在首个DE锁存公共时间。请先看 `team_work/03_ai_soc/SOURCE_VIDEO_CAPTURE.md`。下方网格SOF锁存及旧资源数字为前阶段记录。

最新时间接口：APB v2.2（0x00020002），0x84~0x90为只读公共时间。视频使用完整快照CDC，native在sample_sof锁存；42次回归PASS。详见 `team_work/03_ai_soc/TIME_AND_C24_ACCEPTANCE.md`，下方v2.1结果保留为历史。

2026-10-25更新：A mailbox→C2搬运桥、双完成校验屏障和联合TinyML固件已实现；当前39次RTL回归PASS，新native副本含A桥并综合PASS。APB版本为0x00020001，新增0x80能力寄存器。最新说明见 [C24_AC_BRIDGE_RUNBOOK.md](../../team_work/03_ai_soc/C24_AC_BRIDGE_RUNBOOK.md)，下文保留前阶段记录。

2026-10-24。主开发目录为 `C:\Users\16034\Downloads\FPGA\FPGA_2026_T3_P3`。

本目录已实现可独立仿真的共享内存逻辑。`c2_system_boundary` 把三个内存域访问端口、AI 灰度图写入、跨时钟握手和双槽所有权汇合为**一个 DDR 事务出口**。测试使用合成的 CPU/TinyML/视频主设备和 DDR 行为模型，没有实例化真实 CPU、TinyML 加速器、MIPI、DDR 控制器或 PHY。因此它是 C2 第一阶段的交接成果，尚不构成统一整机工程或可下载配置文件。五个原始 FPGA 工程继续保留。

第二阶段更新：新增 `c2_axi_to_vendor.sv`、`c2_apb_control.sv`、`c2_vendor_attachment.sv`、`integration/` 厂家SoC接入副本，以及 `team_work/03_ai_soc/c2/` 的CPU只读接收/缓存后端。当前回归扩大为34次RTL运行，并包含主机驱动和RV32对象检查。具体接口、寄存器和证据边界以 [C2_VENDOR_APB_CACHE.md](../../team_work/03_ai_soc/C2_VENDOR_APB_CACHE.md) 为准。以下原有边界资源数字保留为第一阶段记录。

## 运行与证据

在项目根目录双击 `13_test_c2.cmd`，或执行：

```powershell
python tools/run_c2_selftest.py
```

依赖项目已有 `tools/iverilog/bin/iverilog.exe`、`vvp.exe` 和 Python 标准库。脚本设置单次编译/仿真超时，编译警告也使回归失败；每次重新生成结果，并记录源文件 SHA-256，避免引用过期 PASS。

- 汇总：`../../logs/c2_selftest.json`。
- 逻辑综合：`../../logs/c2_synthesis.json`、`outflow/c2_boundary.map.rpt`。
- 完整日志：`../../logs/c2/`。
- 基线源码核查：`BASELINE_AUDIT.json`。
- 候选内存图：`memory_plan.json`，明确 `PROPOSAL_ONLY` 和未启用。
- 接口及后续接入：[C2_INTEGRATION.md](../../team_work/03_ai_soc/C2_INTEGRATION.md)。

当前34次回归在原18次基础上，增加ID/窄访问适配、APB、真实厂家DataCache标签失效、SoC接口组合测试。APB以三组时钟比测试，完整图像组合测试也采用三组时钟比及三组DDR随机种子。周期仅用于功能覆盖，没有建立器件时序约束或宣称可运行频率。

`14_synth_c2.cmd` 或 `powershell -NoProfile -ExecutionPolicy Bypass -File tools/run_c2_synthesis.ps1` 仅运行 Efinity map。本轮 Efinity 2026.1/Ti60F225 逻辑综合 PASS：4550 LUT4、4993 FF、2 DSP48、100 ADD；仅为新增边界逻辑，不含 CPU/视频/DDR。异步 FIFO 当前映射为触发器/逻辑，未推断 BRAM；冗余信号清除和逻辑存储映射告警已保留在报告。本次已无位宽截断告警。Efinity 原始告警文件按运行追加，脚本只审核最后一次综合段。

`c2_boundary.xml` 是逻辑综合工程：没有实物引脚/DDR约束，不应用它生成下载文件。此结果不包含布局布线、频率或物理 CDC 验收。

## 文件分工

| 文件 | 已实现行为 |
|---|---|
| `rtl/c2_system_boundary.sv` | 视频请求/授权/事件 CDC、像素异步 FIFO、控制服务和唯一事务出口 |
| `rtl/c2_frame_publisher.sv` | ALLOC→写帧→最后 B 响应→COMMIT；失败 ABORT；CPU 只能 QUERY/ACQUIRE/RELEASE |
| `rtl/c2_buffer_manager.sv` | 两槽状态、generation、字段检查、忙时丢新帧 |
| `rtl/c2_image_writer.sv` | 9216 字节、最多 16 拍突发、4 KiB 边界拆分、FNV-1a、写错后排空本帧 |
| `rtl/c2_memory_hub.sv` | 外部三访问者 + 内部图像写入，共四源仲裁 |
| `rtl/c2_axi_arbiter.sv` | 128 位完整拍 INCR 子集；事务轮询；全局最多一个未完成突发 |
| `rtl/c2_cdc_mailbox.sv` | 完整快照与反压；共同复位取消待处理消息 |
| `rtl/c2_async_fifo.sv` | Gray 指针双时钟 FIFO；顶层深度 16、宽 128 位 |
| `sim/c2_ddr_model.sv` | 小容量字节使能存储模型、随机背压、响应延迟/错误注入 |
| `sim/tb_c2_boundary.sv` | 主交接测试：实际顶层、视频域像素、完整 CPU 读回与故障恢复 |

## 验证边界

主测试每次成功校验 5 张完整图像的全部字节和校验值，检查 4 次拒绝/失败事件、11 次 CPU 控制操作；另有三主设备合计 90 次后台写和 90 次后台读。CPU 还通过 AXI 读回 576 拍图像。成功提交须已收到全部 36 个写响应。错误后下一帧在不复位的情况下读回正确，传输中复位另行验证。

AXI 专项测试覆盖视频配置使用的 128 拍突发、最大 256 拍且恰好结束于 4 KiB 边界的突发，以及逐字节写使能和错误响应路由；这只覆盖受限协议子集，未接厂家主设备。

`sim/tb_c2_image.sv` 保留直接组合测试（像素在内存域），与跨时钟顶层测试分别报告，不能把它当作真实视频时钟验证。`tb_c2_fifo` 对四深度 FIFO 做 2048 个字的多次指针回绕、满/空、反压和共同复位测试。

第二阶段的厂家接口、APB控制和RX只读缓存处理已有代码与离线验证；仍需完成唯一时间源、实际DDR容量/地址转换、真实视频接入、调用新驱动的CPU整机程序、完整整机综合与布局布线、CDC物理约束及板上带宽/缓存/长期实测。当前不产生 FPGA HEX，也不修改 C1 固件。
