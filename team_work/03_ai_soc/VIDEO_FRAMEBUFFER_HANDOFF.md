# C2 完整视频帧缓存与并发验收

> 2026-10-31 更新：本文末尾资源/49 次回归数字是当时历史结果。当前视频双时钟 FIFO 已改为同步读 BRAM，native map 为 39,656 LUT4 / 36,902 FF / 174 RAM10；回归入口已增加为 53 次。详见 [BRAM 优化](BRAM_OPTIMIZATION_20261031.md) 与 [引脚审计](PIN_OWNERSHIP_20261031.md)，最终通过状态以本轮报告为准。


2026-10-25。接续源像素阶段提交 `6153a45`。本阶段把完整 GRAY8 视频写入和显示读出接到 C2 video AXI，和 AI 缩略图 DMA 共用 C2 出口，再经厂家互连 S1 接入唯一 DDR。CPU 保留 S0，TinyML 保留 S2。原五个厂家工程与 A 的三个采样/mailbox 快照不修改。

## A 接线

生成工程：`projects/06_soc_c2/integration/c2_native.xml`，顶层 `c2_tinyml_soc_top`。默认参数是 1920×1080、采样步长20×20。完整视频与 AI 看到**同一组源像素**。

| 顶层端口 | 提供方与约定 |
|---|---|
| `c2_video_clk`、`c2_pixel_vs/de/gray[7:0]` | A 的源时钟域，1像素/拍 unsigned GRAY8；VS高有效且在消隐上升，DE连续覆盖一整行 |
| `c2_display_clk`、`c2_display_vs/de/hs` | A 的显示时序域，1像素/拍的光栅；VS在消隐上升，请求下一显示帧；消隐须留足预取时间 |
| `c2_display_rgb[23:0]`、`c2_out_vs/de/hs` | C2读回灰度扩为 `{gray,gray,gray}`；RGB与输出时序同步寄存，整体比输入时序延迟1拍，接A后续HDMI编码边界 |
| `c2_display_frame_id/timestamp_ms`、`available/failed/busy` | 显示域元数据与状态；`available`表示本次扫描选到完整帧，`failed`表示本次扫描出现欠载/总线错误 |
| `c2_video_published/dropped/write_errors/read_errors/repeated/empty_scans/max_aw_wait/max_ar_wait` | 内存域计数；跨域读取必须做一致性快照，不能逐位接CPU |
| `c2_video_overflow_frames` | 源域FIFO溢出/入口忙计数 |
| `c2_video_underflows/missed_scans/completed_scans` | 显示域欠载、忙时错过VS、完整扫描计数 |
| `c2_map_enable` | 物理地址验收前保持0；只允许在共同复位期间修改，不支持运行中撤销已发出的AXI交易 |

原外部 `c2_video_*` AXI主机端口已改为内部连接。A不再实例化第二个DDR控制器。`c2_capture_record_*` 与AI描述符中的帧号/时间沿用首个源DE定义，完整帧缓存也锁存同一拍的公共时间，并在A完成记录到来时核对它。

**当前物理边界：** 已连接的是源GRAY8和显示RGB/光栅逻辑接口；没有合入MIPI PHY、TMDS编码/引脚或板上时钟。厂家旧视频顶层采用32位RAW打包、16位/双像素读出，不能把它直接当RGB565或直接接本模块的1像素/拍端口。A须明确选择上游RAW到GRAY8、并行像素串行化和对应显示像素时钟；若保留旧双像素HDMI时序，还需加1→2像素打包与时序适配。此项仍待A/C物理集成，不代表已经输出真实HDMI画面。

## 地址与格式

所有AXI地址单位都是**字节**；总线128位，size=4，INCR，最多16拍/突发，完整128位写，4KiB边界不跨越。左上第一个像素位于最低地址/beat最低8位。格式固定GRAY8，行尾补零至16字节边界：

`stride = ceil(width/16)*16`，`frame_bytes = stride*height`，`bank_pitch = align_up(frame_bytes,4096)`。

| 默认1920×1080配置 | 数值 |
|---|---|
| stride / frame_bytes | 1920 / 2,073,600字节 |
| bank_pitch / 三bank总保留 | 2,076,672 (`0x1FB000`) / 6,230,016字节 |
| C2 video相对bank地址 | `0x000000`、`0x1FB000`、`0x3F6000` |
| 候选物理bank地址 | `0x08010000`、`0x0820B000`、`0x08406000` |
| 候选video窗口 | `0x08010000 .. 0x09010000`（不含末地址，16MiB） |
| 独立AI共享窗口 | `0x09010000 .. 0x09020000`；两个9216B图像仍在窗口内偏移`0x1000`、`0x4000` |

这些物理地址仍是提案。实际DDR容量、CPU地址翻译和别名测试未做，默认CPU固件live/MMIO继续关闭。完整视频bank由硬件独占，CPU不读写；CPU的AI图像仍按既有acquire→invalidate→私有副本→release规则，缓存策略不扩展到视频bank。ABI v1和APB v2.2均未变化。默认布局之外，集成包装仅允许16..65535像素宽、正高度，且三份4KiB对齐bank不超过16MiB；AI网格条件还须单独满足96×54。

## 帧生命周期

1. 源端不可反压。每帧首DE发送START元数据，将像素打包成128位DATA，A在下一VS给出完整源帧记录后发送END。无合法VS的启动像素不接收。FIFO溢出后停止该帧DATA，可靠发送错误END并整帧作废；入口来不及结束上一帧时整帧跳过新帧，不从中间一行重新起帧。
2. 内存端选FREE bank置为WRITING；没有FREE则只排空新帧并计丢帧。先预存完整突发再发AW，避免共享DDR等待摄像头像素。
3. 所有DATA数量、源帧号、首DE时间和A完成记录必须一致，且**最终BRESP握手成功**，才将WRITING变为READY。错误BRESP、格式错误或溢出均不发布。尾突发短于16拍时按实际长度发送。
4. 显示VS请求时，取最早READY变为DISPLAY；释放上一DISPLAY前，必须确认上一扫描的输出END已在显示域消费。无READY则重复现有DISPLAY；没有DISPLAY则黑屏。READY/DISPLAY永不被写入方覆盖。
5. 读端先把整个AXI突发收进本地缓存，再送跨域FIFO；显示卡住时不占着DDR等待像素消费。遇RRESP错误，排完当前突发后发ABORT/END，本次扫描标记失败，该DISPLAY在输出结束后释放。异常RLAST/协议违例仍要求共同复位，不声称可无损自愈。
6. 显示缺像素则黑掉本次扫描余下部分，排空旧帧，后续空闲VS重新请求；不把迟到像素平移到后面的坐标。请求未结束时遇新VS会记missed并丢弃旧扫描。已经显示的前缀无法撤回，故显示错误以整次扫描失败计。
7. 摄像头、显示、内存、APB共同异步复位清空FIFO、CDC请求及bank所有权；复位后旧DDR内容不会自动变为READY。只支持共同复位，不支持单侧复位、任一域停钟或运行中修改布局。

## 复现与验证范围

运行 `20_test_video_framebuffer.cmd`。其中 `python tools/run_c2_selftest.py` 执行完整C2回归，随后运行独立尾突发专项和桌面AI输入对照。生成器 `tools/prepare_c2_framebuffer.py` 复用原A源像素/APB/DDR测试结构，实例化实际视频入口、帧缓存和scanout。完整C2回归增至49次：原46次，以及以下3次。

- 1920×1080：完整源帧写入、逐字节DDR核对、完整显示读回逐像素核对，同时CPU/TinyML合成主机读写，AI图像搬运与读回核对。
- 384×216：真实视频写/显示读、AI缩略图DMA、CPU和TinyML合成主机同时争用同一个DDR模型。验证首DE元数据、最终B屏障、不撕裂、重复显示、无空bank丢帧、错误源尺寸、显示欠载与恢复、BRESP/RRESP错误、源FIFO溢出与恢复、AXI写入途中共同复位。
- 383×216、另一时钟比及随机种子：同上，并逐行核对stride=384时最后一个补零字节。

独立专项 `python tools/check_c2_video_tail.py` 已PASS：32×3、每帧6个128位字，检查AWLEN/ARLEN=5、最终B响应屏障、随机显示反压和重复扫描。报告为 `logs/c2_video_tail.json`，单独绑定相关RTL、测试与执行器源码SHA。

每次PASS行记录DDR完整帧字节数、显示像素数、CPU/TinyML突发次数、与AI搬运重叠的请求、读写重叠、仲裁等待峰值（内存时钟周期）。`logs/c2_selftest.json` 绑定RTL、测试、生成器的SHA；日志位于 `logs/c2/tb_c2_framebuffer*.log`。`19_test_video_capture.cmd` 同样运行整个49次回归，随后做既有桌面AI输入对照。

PASS行的等待峰值直接在序列器后的C2/video及厂家互连输入观察。顶层 `c2_video_max_aw_wait/max_ar_wait` 计数则位于帧缓存与序列器之间，序列器立即接收时可为0；它们不等价于全链路仲裁延迟。溢出计数包括检测到的FIFO溢出/START排队失败，`dropped`只统计已经送达内存端的整帧丢弃；源端在上一帧END尚未排完时跳过的新帧不会经过内存端，不能仅凭`dropped`当作摄像头总丢帧数。

故障并发用例的等待峰值包括主动暂停DDR接收新突发的注入区间，不能当作正常仲裁延迟上界；未注入暂停的1080p用例单独记录正常争用下的峰值。384×216用例已核对414,720字节bank数据及663,552个显示像素，记录63次与AI搬运重叠的请求、117,113个读写重叠周期，CPU/TinyML各28,042组后台读写。

本阶段native map已PASS：52,802 LUT4、53,312 FF、51 DSP48、6,705 ADD。新视频FIFO和突发暂存当前映射为逻辑存储，资源开销明显增加；物理集成前应优先评估同步读双时钟BRAM实现并重验CDC/欠载行为，不能据map结果承诺还能放下完整MIPI/HDMI。存量A/厂家告警及本次逻辑存储映射告警见 `logs/c2_native_warning_review.json`，没有宣称全部消除。

完整1080p用例已逐字节/像素核对2,073,600字节写入和2,073,600个显示像素；同次CPU、TinyML合成主机各完成92,715组读写，视频仲裁点AW/AR等待峰值为63/61个内存时钟周期。这些数字属于固定种子和行为模型的一次仿真，不是板上性能指标。

最终离线验收：49次RTL回归、独立尾突发专项、主机驱动、RV32对象/缓存指令检查、native map、两条桌面AI读回对照及697项C24包身份检查全部PASS，原C1仍为527项PASS。RV32编译器有一次`cc1.exe`子进程启动失败，未修改源码/工具链即重试成功；`logs/c2_selftest.json` 的 `postcheck_recovery`保留原始失败、重试报告时间与全部源哈希复核结果。CPU固件版本仍是`c24-d1fc40db3541b41f`，没有重写固件或板卡。

功能测试采用**合成CPU/TinyML AXI主机和DDR行为模型**，未执行真实CPU推理指令、厂家加密互连或DDR PHY。native map另实例化真实CPU/TinyML、厂家互连和一个DDR控制器；map不证明物理时序、CDC签核、1080p帧率/带宽、真实HDMI或板上推理。上板前仍须接好物理视频/双像素适配、确认板卡DDR/引脚/时钟/SDC，完成P&R与带宽压力验收。
