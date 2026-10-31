# 2026-10-31 C2 视频 FIFO BRAM 优化

native Efinity map 已通过。把视频入口和显示出口两个 130 bit × 64 深度的异步 FIFO 改为同步读双时钟 RAM，原有 DDR 布局、帧角色、首 DE 时间戳、128 bit AXI、APB v2.2 和 CPU 固件 ABI 均保持原定义。

| Efinity 原语 | 优化前 | 优化后 | 变化 |
|---|---:|---:|---:|
| EFX_LUT4 | 53,027 | 39,656 | −13,371，约 −25.2% |
| EFX_FF | 53,539 | 36,902 | −16,637，约 −31.1% |
| EFX_RAM10 | 160 | 174 | +14 |
| EFX_DSP48 | 51 | 51 | 0 |
| EFX_ADD | 6,715 | 6,715 | 0 |

两次均为相同 Ti60F225、Efinity 2026.1.132、native CPU/TinyML/单 DDR overlay 的 map 统计。基线为提交 `7d4dc77` 的本机综合，保存于 `logs/c2_bram_baseline_20261031.json`，含原报告哈希及源身份。综合后的网表在 `c2_full_video/ingress/crossing/memory`、`c2_full_video/framebuffer/output_cdc/memory` 各有 7 个真实 EFX_RAM10 实例。资源下降不是仅根据 RTL 数组估算。

## 实现与行为约束

- 新增 `projects/06_soc_c2/rtl/c2_bram_async_fifo.sv`，只替换完整视频入口 `crossing` 和帧缓存出口 `output_cdc`；AI/旧逻辑继续使用原 `c2_async_fifo.sv`。
- RAM 写口和同步读口都没有 reset/初始化，便于推断 BRAM；复位只清指针、同步器和 valid，不需要擦除 RAM 数据。
- 读地址提前选择当前或下一未消费元素。读指针只在 `valid && ready` 消费时推进，预取到输出寄存器不会提前释放槽位，因此容量仍严格等于 64，不会变成 65，也不会在背压时覆盖未消费字。
- 使用原 Gray 指针和双级同步器；源/目的两域均要求运行时钟及共同复位。复位丢弃旧所有权，释放后不发布未初始化 RAM；不支持单侧复位或停钟。
- `d_data` 在 valid=0 时无有效数据语义；valid=1 且背压期间必须稳定，连续可读时每目的时钟可消费一字。物理 CDC 路径、Gray 总线偏斜、异步域约束及 RAM 时序仍需最终 SDC/P&R 验证。

## 验证入口

`python tools/run_c2_selftest.py` 现在包含 53 次 RTL 仿真：新增的 3 次 FIFO 对照使用 3/11、11/3、5/5 半周期组合，各搬运 4096 个 130 bit 字，逐拍对比旧 FIFO 的 ready、valid 和有效数据，并覆盖精确满容量、随机背压、输出保持、多次指针回绕、满队列共同复位。

完整回归同时覆盖 1080p 视频写入与显示读回、AI DMA、CPU/TinyML 合成 AXI 主机并发、源溢出、显示欠载、总线错误和复位恢复；独立尾突发工具已补入新 RTL 依赖。桌面推理仍只校验传输结果与固定参考一致性，不代表 FPGA 已运行推理或真实摄像头/HDMI 已接通。

复现综合和结果绑定：先执行 `python tools/prepare_c2_vendor.py`，再执行 `tools/run_c2_synthesis.ps1 -Target native`；完整回归完成后执行 `python tools/audit_bram_usage.py`、两条 `tools/check_a_c2_pc.py` 对照（其中一条带 `--video-capture`）、`python tools/verify_c24_package.py`。综合和回归会生成本机报告，不能把仓库内历史绝对路径报告当作接收电脑的新验收。

本轮最终结果：53 次 RTL 回归、主机驱动与 RV32 编译、独立尾突发、native map、两条桌面输入对照、5 张 A 真图/100 条 B 热图离线回放及 781 项 C24 包身份检查全部 PASS。当前 CPU 固件仍为 `c24-ddfd364d754dce06`，二进制未改；pin 审计执行成功，物理就绪状态仍为 `REVIEW_REQUIRED`。

1080p 本轮逐字节/像素核对各 2,073,600 字节，CPU/TinyML 合成主机各完成 92,715 组后台读写，AW/AR 等待峰值仍为 63/61 个内存时钟周期；只表示该固定模型/种子的仿真结果。

## 仍有空间与限制

视频 `wbuf/rbuf`、AI 像素 FIFO、AI writer 突发缓存这四处各 2048 bit 的存储仍为逻辑存储。本轮优先移除两个各 8320 bit 的最大开销，没有更改它们的握手路径。今后若继续优化，需分别实现同步读预取并验证 AXI 背压与尾突发。

新增 14 个 RAM10 有真实资源成本，宽而浅的 FIFO 并未用满各块容量。map 通过不能证明完整 MIPI/HDMI 最终可布通、1080p 带宽充足或电气/CDC 合格。本轮没有改 CPU 固件、生成整机可下载 bitstream 或访问板卡。引脚/Bank/PLL 审计见 `PIN_OWNERSHIP_20261031.md`。
