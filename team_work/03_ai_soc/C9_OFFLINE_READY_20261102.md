# C9 本地准备与下次接板顺序

> 实板更新：下述两个待测对照已测试。C9 COMB4=0两次校准通过且CPU可运行；C8 COMB4=1失败，原C8全容量复核通过。当前入口和剩余项以 `DDR_FIX_BOARD_RESULT_20261102.md` 为准，下方保留接板前计划作为历史。

2026-11-02：板卡未连接。本轮仅完成本地构建、时序/身份审计及离线测试，未打开串口、下载镜像或写 Flash。

## 结论与矩阵

原 C10 的 CPU、DDR/缓存、六组静态 TinyML 与 Flash 冷启动结论保留。C9 的 DMA 缓存交接及真实视频并发尚未实板通过，阻塞点仍是 DDR 校准未完成、CPU 保持复位。

| 镜像 | 构建条件 | XLR | setup / hold (ns) | 实板结果 |
| --- | --- | ---: | --- | --- |
| C9 USER2 cong | COMB4=1，CONGESTION_2，seed2 | 60208 | +0.041 / +0.026 | cal=0，状态0x17 |
| C9 USER2 speed | COMB4=1，CONGESTION_2，seed1 | 60432 | +0.120 / +0.026 | cal=0，状态0x03 |
| C9 USER2 nopack | cong，COMB4=0，CONGESTION_2，seed2 | 60374 | +0.254 / +0.026 | 待测 |
| C8 独立 DDR 对照 | 原 C8 只改 COMB4=1 | 6859 | +0.398 / +0.028 | 待测 |

原 C8 已通过全256 MiB四图案和地址别名检查。C9 nopack 保留 cong 对照全部功能RTL、DDR参数、引脚、电压和时钟约束；C8对照只改变打包选项。speed 的 seed2 曾出现负setup并被拒绝使用；seed1改变了物理实现，不能把实板状态差异仅归因于综合mode。

已捕获 KEY0 有效按下/松开。USER2 观察到控制器复位已释放、4 PLL锁定、4功能时钟有活动，延时计数稳定300000。多位原生状态不是原子快照；时钟活动不确认实际频率/相位。本项目同版 DDR IP v1.1 的0x03、0x17和debug_port=0x200010000定义尚缺，不猜测具体训练阶段。

## 已准备的镜像与工具

- C9 nopack：`build/c9_ddr_probe_nopack_20261101`，位流 SHA256 `e780083e22b4383cf2dbf5088a7a3f93e9a81698fda1dcfec30f0169a99a7c04`。
- C8 COMB4：`build/c8_comb4_on_20261102`，位流 SHA256 `5a579a54ec9fb8b1d8a9ecc367decb42c24478e5c475601b3d0e5dbad88606e1`。
- 统一检查：`tools/check_c9_offline.py`；结果 `logs/c9_offline_readiness_20261102.json`。
- C8 生成/审计：`tools/c8_comb4_control.py --prepare` → `tools/run_c8_comb4_control.ps1` → `tools/c8_comb4_control.py --audit`。生成器拒绝覆盖已存在实验，不重新生成已完成版本，不覆盖原C8报告。
- C8采集：`tools/capture_c8_comb4_control.py`。严格要求两条全容量PASS，结束后尝试恢复C10。
- 固件采集：`tools/run_ram_diagnostic.py --configure-probe nopack`明确选择已审计对照，完整读回固件后才设置应用入口执行。ROM停驻镜像属于诊断用途。

离线预检在导入串口库前退出。测试覆盖三份真实固件身份，以及替换位流、修改RTL、缺失位流绑定、审计未完成四种拒绝情况。探针RTL的bank、复位独立性、TAP隔离、运行/停止时钟仿真通过。

项目根目录下可随时重复的纯本地命令：

```powershell
C:/Python311/python.exe -X utf8 tools/check_c9_offline.py
C:/Python311/python.exe -X utf8 tools/capture_c8_comb4_control.py --preflight-only
C:/Python311/python.exe -X utf8 tools/run_ram_diagnostic.py --record firmware/c9_dma_diag/BUILD_RECORD.json --binary firmware/c9_dma_diag/c9_dma.bin --prefix 'C9|' --configure-probe nopack --preflight-only
```

## 接板后执行，本轮未执行

保持原USB口与已验收驱动，确认UART为COM13；若端口变更先确认对应设备。硬件测试逐个执行，不并行占用USB或DDR。

1. 审计C9 nopack后，运行 `python -X utf8 tools/run_c9_ddr_control.py --capture`。新入口调用冻结的SDK采集脚本，保存采集源码，并按原始USER2数据严格判定校准；仅状态采集成功不算校准通过。底层仅临时配置SRAM，结束后尝试恢复C10并核对六组TinyML。默认不加`--capture`时只做离线预检。
2. SDK Python运行 `tools/capture_c8_comb4_control.py --port COM13`，完成小工程对照。它是独占DDR的破坏性内存诊断，不写Flash。检查全容量结果和C10恢复结果。
3. 仅当C9校准完成、CPU复位释放，才在同一nopack镜像执行 CPU/DDR → DMA缓存交接 → 真实摄像头并发。每次保留镜像SHA、固件清单、完整DDR读回SHA和UART。
4. DMA必须同时证明省略invalidate读到旧值、执行invalidate读到新值、旧token拒绝、租约保护及视频/扫描计数进展。摄像头须真实寄存器回读、12帧结果、至少6次有效推理，并保存私有输入与桌面INT8参考比对。
5. 没有HDMI显示器时，内部扫描计数不能作为物理HDMI画面通过。C9诊断暂不含C3，最终仍需回归含C3的完整工程。
6. 每轮结束恢复C10并记录恢复结果。本轮对照无需改写已通过冷启动验收的Flash。

SDK环境示例（后续接板才运行采集）：

```powershell
$taskEf = Join-Path (Get-Location) 'tools/efinity/2026.1'
$env:PYTHONHOME = Join-Path $taskEf 'python311'
$env:PYTHONUTF8 = '1'
& "$taskEf/python311/bin/python.exe" tools/capture_c8_comb4_control.py --port COM13
```

若nopack仍不能校准，结合小工程结果准备厂家复现资料，并补同版IP状态码/调试端口定义后再决定下一处改动。不以放宽时序约束代替修复。

## 交接

本轮代码和审计报告复制到本地交接仓库，未提交或推送GitHub。SDK、完整厂家私有RTL、原始Flash备份、摄像头原图和整个build目录不打包交接。主项目私有构建保留供下次接板使用。
