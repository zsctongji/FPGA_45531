# C9 DDR 只读 USER2 探针

这是独立的实现诊断，不是整机发布版本。基础工程和已验收 C10 不改动；生成目录为 `build/c9_ddr_probe_20261101`。CPU 启动入口停驻于 ROM，不读取 SPI 或装载应用。新增探针的唯一输出是 USER2 TDO，不控制 DDR、CPU、复位或 PLL；LED0/LED1 只观察 cal_done/io_systemReset。外部引脚、电压、DDR 参数以及原功能时钟约束保持原值，新增 USER2 TCK 约束。

## 流程

1. 在项目根目录执行 `python -X utf8 tools/test_c9_ddr_probe.py`。
2. 执行 `python -X utf8 tools/prepare_c9_ddr_probe.py`，只生成一次独立副本，拒绝覆盖已有目录。
3. 执行 `powershell -NoProfile -File tools/run_c9_ddr_probe.ps1`，完成接口、综合、P&R、STA/CDC 和位流生成。
4. 执行 `python -X utf8 tools/audit_c9_ddr_probe.py`。只有得到 `PASS_OFFLINE_READONLY_DDR_PROBE` 才允许下一步。
5. 用 Efinity 自带 Python 运行 `tools/capture_c9_ddr_probe.py`，并设置匹配的 `PYTHONHOME`。工具按审计身份临时配置 SRAM，采集 USER2，随后恢复 C10 并核对六组 TinyML。它没有 Flash 写入或 EXTEST 操作。

RTL 仿真覆盖应用复位保持下读取、四个 bank、未选中 TAP 的隔离，以及运行/停止时钟观测。仿真通过不等于实现、时序或实板通过。

## 36 位 DR 协议

Ti60 BSDL 的 USER2 指令为 `01001`。DR 低位先移出；位 35:32 为 bank（0…3），低 32 位为状态。每次选中 USER2 后 CAPTURE 自动切到下一 bank。TDI 只填充已读出的移位寄存器，不影响这次 CAPTURE 后移出的前 36 位，也不更新 bank 或任何功能控制。无写控制命令。

| Bank | 32 位状态 |
| --- | --- |
| 0 | bit0 cal_done；bit1 io_systemReset；bit2 sys_rst；bit3 ddr_rstn；[10:4] init_cur_state；[18:11] wrlvl_dq_check；[26:19] rd_level_dqs_check；其余为 0 |
| 1 | bit0 idelay_ld；bit1 mpr_rdlvl_dly；[4:2] wrlvl_shift；[7:5] rdlvl_shift；[27:8] 初始化延时计数 cnt；其余为 0 |
| 2 | ddr_debug_port[31:0] |
| 3 | [31:16] 固定签名 C9D2；bit12 root_reset_n；[11:8] PLL4/i_pll/user_pll/pll 四个锁定信号；[7:4] rx/tx/system/core 四个相位观测；[3:0] ddr_debug_port[35:32] |

四个时钟各驱动周期为 7 的小型相位序列，单比特经两级 TCK 同步。连续读到 0 和 1 表示观察到了该时钟的活动，不能据此确认频率；未观察到变化也不单独证明时钟停振。

原生多位状态和不同 bank **不是原子快照**。采集工具保存原始包，检查 bank 连续性和 C9D2 签名，再报告末八次 bank0/bank1 是否相同。仅用重复稳定的阶段/计数值判断停滞，不把训练过程中暂态或撕裂值当作结论。

结果写入 `logs/c9_ddr_probe_20261101/<时间>/`；其中 `attempt.json` 明确记录配置身份、观察结果、Flash 未写入和 C10 恢复结果。
