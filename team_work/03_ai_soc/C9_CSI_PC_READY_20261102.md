# C9 CSI 观测探针电脑端准备

状态：电脑端工作已完成，等待下一次实板采集。本轮仅构建和读取本地文件，不打开 JTAG、串口，不重新下载板卡，不写 Flash。正式诊断入口 `config/c9_active_profile.json` 继续使用已通过实板图案 DMA 的 display 镜像。

## 探针用途

既有实板记录已经确认 C2 收到的连续 DE 段最大只有 72 像素，段数超过 4095；它还不能证明断续发生在 CSI 输出还是后续 ISP/串并转换。

新工程 `build/c9_phy_geometry_image_20261102` 在原 CSI 像素时钟域累计最后一条非空 HS 的 payload 组数和 valid 连续段数。它同时保留上一版 C2 帧宽/段数观测，像素数据路径及控制时序不改动。两组记录不保证跨时钟域同时发生。

phy 快照 bank=4、pair=0 的 hi：31:22 为 payload groups，21:12 为 valid runs，bit11 为 seen，bit10 为计数饱和，bit9 为曾出现 valid 且 HS 为低，bit8:1 保留零，bit0 保留 camera_fault。lo 保留原 MIPI debug。

## 本地检查

```powershell
C:/Python311/python.exe -X utf8 tools/test_c9_phy_geometry.py
C:/Python311/python.exe -X utf8 tools/test_c9_phy_geometry_decode.py
& tools/run_c9_phy_geometry.ps1
C:/Python311/python.exe -X utf8 tools/audit_c9_phy_geometry.py
C:/Python311/python.exe -X utf8 tools/report_c9_phy_geometry.py
```

RTL 专项测试覆盖连续/分段输入、首周期 valid、空 HS、计数饱和、HS 外 valid、原 fault 透传和复位。解码器 11 项合成测试覆盖合法数据与异常拒绝。合成测试不能作为实板证据。

生成器用于第一次创建隔离工程，不能覆盖已存在目录；本机暂停恢复应直接运行已有 runner。runner 必须指向 `build/c9_phy_geometry_image_20261102`，不要指向旧 display 或 geometry 工程。

## 后续上板入口

默认命令只核对镜像、固件及源文件身份，USB/串口不访问：

```powershell
C:/Python311/python.exe -X utf8 tools/run_c9_phy_geometry.py
```

下次明确开始实板测量时才使用：

```powershell
C:/Python311/python.exe -X utf8 tools/run_c9_phy_geometry.py --capture --port COM13
```

该命令会读 USER2 校准状态、装载并完整回读 3508 字节诊断固件、采集十秒，再恢复 C10。`CAPTURED_CSI_GEOMETRY_ONLY` 只表示诊断记录完整，不代表真实视频、DMA、TinyML 或冷启动验收通过。该镜像扩展了 phy 的 hi，不能套用旧摄像头验收器对整个 hi 为零的判断。

## 如何使用实测结果

| 观察结果 | 下一项判断 |
|---|---|
| 每条 HS 约 480 个 groups，但 valid runs 大于 1 | 在当前四像素/组配置下总 payload 对应 1920 像素；检查行内断续及 ISP 输入的行边界适配 |
| 每条 HS 480 个 groups、1 个 valid run，但 C2 仍为短段 | 继续定位 RAW 串并转换、ISP 输出或 GRAY 串并转换边界 |
| groups 不是 480 | 核对实际 payload、像素打包、HS 极性及接口配置；不能用寄存器回读尺寸代替 payload 测量 |
| clipped、valid_outside_hs 或 fault 出现 | 保留异常，结合原始日志判断计数范围和控制对齐，不能直接拼接为完整行 |
| seen 为 0 或日志不完整 | 诊断证据不足，不能据此选择视频修复方案 |

480 groups 对应 1920 像素是当前 RAW10 四像素/组接口配置下的推断，仍需结合实际数据类型和 payload 核对。若需要行缓冲，必须同时验证行长、帧边界、像素顺序、截断/溢出拒绝及复位恢复；不能只延长 DE 或忽略无效周期。A 的 ISP 内部也使用 DE 边沿换行，修复位置需要覆盖 ISP 输入的行语义。

DDR 参数、校准算法、坏帧拒绝和 1920×1080 验收要求保持不变。具体构建结果以 `logs/c9_phy_geometry_ready_20261102.json` 为准，新的实板测量仍待完成。

## 本轮完成结果

- 完整 interface、map、P&R、STA、位流生成通过；只在电脑生成文件，没有执行下载。
- 60571/60800 XLR，RAM224/256、DSP60/160；setup +0.223 ns、hold +0.026 ns；66 位 Gray CDC 两角检查通过。
- 专项 RTL 仿真通过，11 项 CSI 解码测试通过；固件与镜像离线身份检查通过。
- 位流 SHA256：`da4d195aa3181ff382b043f5c32f68482352a8f187a2da89965e012880ad73b4`。
- 审计 SHA256：`5f34943de1dcfb1bbfd46a9601dc8b9744d91918d04389858b9b88d7dae9525e`。
- 诊断包 `fpga_bitstreams/c9_phy_geometry_100mhz` 含 bit/hex、资源/引脚/时序/CDC 报告、冻结实现审计及 BUILD_RECORD；原 3508 字节固件保持不变。
- 正式 active profile 未改变。新探针尚未实板校准或采集，不能把旧 geometry 镜像的实板校准结果转移到这一版。

本轮文件与前一阶段尚未交接的观测源码、固件、公开状态日志一起复制到本地 `FPGA_cooperation_handoff`，复制前检查已存在文件，覆盖前留备份，复制后逐项核对 SHA256。未复制 SDK、完整厂家源码、原始 Flash 内容或相机图像；未提交或推送 GitHub。复制结果见 `logs/c9_pc_handoff_20261102.json`。
