# C9 DDR 校准阻塞解除与实板对照结果

> 后续更新：启动显示漏扫描已修正，修正版通过实板DMA/图案视频并发，当前C9入口改用display配置；真实摄像头源格式仍未通过。最新状态见 `C9_DISPLAY_FIX_20261102.md`。本文件保留DDR专项阶段的原始范围。

2026-11-02，Ti60F225，Efinity 2026.1.132，原USB口/libusbK/COM13。

**当前C9诊断配置通过关闭 `pack-luts-to-comb4` 恢复DDR校准和CPU访问。DDR参数、校准算法、校验标准均未修改。** 已固定该配置作为C9诊断加载入口；原失败镜像保留用于复现，不覆盖历史证据。

此结论适用于本次实测构建，不宣称已证明工具厂商内部根因，也不代表完整整机验收通过。

## 受控实板对照

| 实测 | 结果 | 原始证据 |
| --- | --- | --- |
| C9 cong/COMB4=0，第一次 | cal=1，CPU reset=0，状态0x16 | `logs/c9_ddr_probe_20261101/20261102_182836` |
| 独立C8仅开启COMB4 | UART字段固定字符异常，无完整容量PASS，严格拒绝 | `logs/c8_comb4_control_20261102/20261102_183007` |
| 原C8 COMB4=0复核 | 256 MiB四图案及地址别名检查通过；N=04000019，两条完整PASS | `logs/c8_comb4_baseline_20261102/20261102_183426` |
| 原C9 cong/COMB4=1复核 | 再现cal=0、CPU reset=1、状态0x17 | `logs/c9_ddr_probe_20261101/20261102_183619` |
| C9 cong/COMB4=0，第二次 | 再次cal=1、CPU reset=0、状态0x16 | `logs/c9_ddr_probe_20261101/20261102_183801` |
| C9 COMB4=0，实际CPU程序 | 固件7836字节完整读回一致，CPU启动，6地址/24word检查与DMA数据测试执行完成 | `logs/ram_diagnostic_20261101/20261102_183914` |

两个C9 cal结果均通过现有严格原始包判定；不是把“采集进程正常退出”改称校准通过。开启COMB4的C8日志有畸形字段，不能依据其中看似状态码的字符推断具体训练阶段，结果仅按原校验器判为失败。

C9对照保留同一cong模式、CONGESTION_2、seed2、功能RTL、原DDR/时钟/IO配置，只改变COMB4选项并重新实现。静态比较还验证三个C9实现与C10的49个DDR IO组件、119个公共生成外围实例以及控制器源码输入；参数include路径不同处已核对实际参数内容相同。证据支持当前采用关闭COMB4的配置，不推广成所有器件/版本的通用结论。

## CPU与内存证据的范围

在关闭COMB4的同一C9位流上，原有 `c9dma-3739cbec6825e6db` 固件完整写入和回读SHA一致，实际执行至DONE。6个DDR地址互不别名；两张9216字节图案/FNV、缓存旧数据负例、invalidate后新数据、旧token拒绝及租约保护均输出PASS。DDR AXI读写错误计数为0。

**完整DMA/视频并发验收仍为FAIL。** 原 `tools/check_c9_uart.py` 检出显示侧 `missed_scans=1`：测试前为1、测试后仍为1，underflow为0。未放宽计数条件，也未将局部数据测试通过冒充完整并发通过。下一项应定位该启动显示扫描记录，而非继续改DDR校准参数。

CPU证据来自C9专用诊断；未把要求map=0的C7诊断硬套到固定map=1的C9。全256 MiB容量证据属于原独立C8，当前C9尚未运行全容量测试。真实摄像头推理、物理HDMI、C3并发、C9 KEY0及冷启动仍需各自验收。

## 已固定的可用配置

- 配置文件：`config/c9_board_profile_20261102.json`，cong、COMB4=0、CONGESTION_2、seed2。
- 位流：`fpga_bitstreams/c9_nopack_100mhz/soc_physical.bit`，SHA256 `e780083e22b4383cf2dbf5088a7a3f93e9a81698fda1dcfec30f0169a99a7c04`。
- setup/hold最小裕量：+0.254/+0.026 ns；60374/60800 XLR；原66位Gray CDC双角检查通过。
- `tools/run_ram_diagnostic.py --configure-c9` 现选择上述已验收DDR诊断配置，不再默认加载开启COMB4的原失败版本；显式`--configure-probe cong`仍保留复现入口。
- 本位流是暂不含C3、ROM入口停驻的诊断镜像，须显式加载匹配CPU程序，不是Flash自动启动发布版本。

仅离线核对示例：

```powershell
python -X utf8 tools/run_ram_diagnostic.py --record firmware/c9_dma_diag/BUILD_RECORD.json --binary firmware/c9_dma_diag/c9_dma.bin --prefix 'C9|' --configure-c9 --preflight-only
python -X utf8 tools/report_ddr_fix.py
```

`tools/report_ddr_fix.py` 从原始记录重建范围明确的汇总 `logs/ddr_fix_20261102.json`，并生成诊断产物清单。原校准及并发校验器的判断标准保持不变。

## 板卡与交接状态

最后于18:40:15～18:40:34恢复C10，六组静态TinyML与参考结果一致；证据 `logs/c10_warm_boot_20261101/20261102_184015`。本轮未写Flash；现有Flash冷启动基线未改动。

本轮源代码、配置、诊断位流和选定原始日志同步至本地交接仓库，未提交或推送GitHub。SDK、完整厂家私有RTL和Flash原始备份不纳入本轮交接。
