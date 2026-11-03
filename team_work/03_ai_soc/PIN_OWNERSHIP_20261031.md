# 2026-10-31 引脚与物理资源合并审计

电脑端审计完成，结论为 **REVIEW_REQUIRED，最终物理约束尚未就绪**。没有操作板卡、串口、JTAG、Flash 或蜂鸣器。不同独立工程的同脚使用不是正在发生的电气争用；下文指出的是把这些工程合为一个映像时必须解决的所有权冲突。

## 核对依据与范围

`tools/audit_pin_ownership.py` 只读解析 9 份 Ti60F225 `.peri.xml`：已核验 SHA-256 的 A 20261029 工程包内 11/12/13 三工程、B 20261030 包内 `standalone_sensor_fast`，以及本地 01/02/03/04/05 基线。报告 `logs/pin_ownership_audit_20261031.json` 保存逐脚所有者、方向、电平标准、源哈希、A13/C 重叠项、Bank 差异和 PLL 重叠。

球位来自已安装 Efinity 2026.1.132 的 `pt/db/devicemap.csv` 对 Ti60F225 的选择及相应 package XML；处理带 `_CLK`/`_CDI` 的复用后缀，歧义别名直接拒绝。J28 针号沿用 B 的接线资料，器件库不能证明 PCB 转接方向或实际连通性。7 个反例/边界检查覆盖同脚双所有者、输出与复位输入冲突、电平差异、相同声明合并、未分配状态及封装别名。

工具检查 GPIO 声明和已声明的 Bank/PLL 资源；不是完整 Interface Designer 合法性检查，不替代 MIPI/DDR 专用资源、管脚复用、差分配对、供电、时钟布线和 P&R 验证。

## 需要处理的引脚

| 球位 / GPIO / 外部针号 | 已有占用 | 最终合并处理 |
|---|---|---|
| B3 / GPIOL_04 / J28.37 | 旧 02/04/05：`LCD_RST_P` 输出；A 11/12/13：同名输入；B：`sensor_scl` 双向 | 移除旧 LCD 驱动和重复 pad 实例，由 C3 SCL 唯一拥有；输出数据固定 0、OE=`drive_low`、输入来自实际 pad |
| C3 / GPIOL_06 / J28.39 | 旧 02/04/05：`LCD_POWER` 输出；A 新工程：同名输入；B：`sensor_sda` 双向 | 与 SCL 相同；A 的输入释放只是避免旧输出，尚未接到 C3 控制器 |
| B5 / GPIOL_10 / J28.38 | A：`buzzer_sig` 输出；B：同名输出；C3 计划输出 `c3_buzzer` | 替换为唯一 C3 pad 所有者，不能同时保留 A 常量驱动与 C3 驱动；核验极性和冷启动静音 |
| P13 / GPIOR_27 | A `led[0]` 输出；B `led_data[0]` 输出；TinyML 基线 `i_arstn` 输入 | **硬合并冲突**。先核对板图与真正的复位来源，再决定保留的单一用途；不能直接把 A LED 总线和 C 复位约束拼接 |
| N13 / GPIOR_24 | A `led[1]`、B `led_data[1]` 输出 | 可能作为报警 LED 的备选，但已经有诊断所有者；未选定、未确认极性，不在本轮冻结 |
| D12 / GPIOR_20；B14 / GPIOR_18 | A 摄像头 `io_cam_scl/io_cam_sda` 双向，3.3V 声明 | 与 B3/C3 的传感器总线是两组不同 pad；保持独立，不因同叫 I²C 就短接 |

A13 与 C TinyML 基线共有 50 个 GPIO 声明：49 个名称/方向/电平相同，仍需合并为单个 pad；唯一不兼容的是 P13。相同 DDR 声明不代表可以保留两个 DDR 控制器或两套 PHY，仍执行唯一 DDR 控制器架构。上述 3.3V 是约束声明，未测量板上电压。

## Bank、PLL 和未绑定项

- A13 与 C 基线的 Bank 默认值不同：2B 为 1.2V / 1.8V；3A 为 1.8V / 1.2V。不能通过复制某一份默认值解决，需要核对真实供电和最终使用资源。
- `PLL_TL0` 同时被 A 的 MIPI_TX_PLL 和 C 的 pll_inst1 声明；虽然参考频率与倍/分频字段相同，输出路由、相位、复位和用途仍须逐项合并。
- `PLL_BR0` 被 A 的 pll_inst4 和 C 的 DDR3_PLL 使用，倍/分频配置不同。需要统一时钟资源方案；A 自身还有 `PLL_TR0` 的 DDR3_PLL，不能把这些名称视作同一个物理 PLL。
- native C2 工程的 `inter_file` 为空，没有最终板级 `.peri.xml`。`c3_pad_contract.json` 仍为 `REFERENCE_ONLY_NOT_APPLIED`；`c3_io_enable` 在验收前的板级包装中必须显式接 0，不能悬空当作 0。
- 报警 LED、开漏 OE 实体映射、实际输入反馈、Bank 供电/上拉、上升下降时间、复位来源、蜂鸣器驱动/极性和 SDC/CDC 都未闭环；本轮没有生成可安全烧录的整机 bitstream。

## 下一次交接的具体内容

A 提供最终 MIPI/显示 pad 与时钟约束，处理旧 LCD 输出、LED 和 PLL 的合并。C 基于确认的板型建立唯一的整机 Interface Designer/SDC，接 C3 开漏 pad、复位与唯一 DDR，重新跑接口检查和 P&R。B 核对 J7/J26/J28 方向、接线连续性、实际 IO/上拉电压和蜂鸣器极性，随后再进行受控总线/报警验收。

复现：安装本工程约定的 Efinity 后，准备上述两个固定 SHA 的工程包至 `build/team_real_20261031`，执行 `python tools/audit_pin_ownership.py`；也可用 `--a-archive` 和 `--b-archive` 指定路径。`--require-ready` 在当前未闭环状态返回 2，供后续发布门禁使用。报告执行成功与物理就绪分别记录，不能用 `audit_execution=PASS` 表示可以上板。
