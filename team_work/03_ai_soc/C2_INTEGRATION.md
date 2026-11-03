# C2 第一阶段交接：共享 DDR 功能边界

日期：2026-10-24。实现位于 `projects/06_soc_c2/rtl`；测试说明见该目录 README。板卡暂时不在手边；本轮验证属于电脑端 RTL 功能仿真。

后续状态已更新到 [C2_VENDOR_APB_CACHE.md](C2_VENDOR_APB_CACHE.md)：厂家接口适配、APB寄存器和RX缓存后端已有实现，回归为34次，并生成独立厂家SoC接入副本。下文保留第一阶段接口和待办背景；涉及“APB/厂家接入尚未实现”的描述以第二阶段说明为准。物理地址、板上缓存、真实视频和最终时序仍待验证。

## 现有工程的接入核查

`tools/audit_c2_baselines.py` 从当前文件读取参数，输出带源码 SHA-256 的 `projects/06_soc_c2/BASELINE_AUDIT.json`。发现：

1. TinyML 顶层有一个 `ddr3_top`，互连 `S_COUNT=3`，S0/S2 用于现有 CPU/TinyML 路径；S1 的请求线只出现于声明和互连拼接，没有生产者连接。预留端口不代表视频已接入。
2. 视频 `frame_buffer` 的 `START_ADDR=0`、`I_VID_WIDTH=32`、`O_VID_WIDTH=16`、`MAX_VID_WIDTH=960`、`MAX_VID_HIGHT=1080`、`FB_NUM=3`、`BURST_LEN=127`。按输入位宽和最大尺寸估算三缓存约 12,441,600 字节，地址步长和内部打包仍须对照厂家实现确认。
3. CPU linker 起点 `0x1000`、长度 128 MiB，结束地址（不含）`0x08001000`。视频从零开始会与程序分配区冲突，必须改基址并验证 CPU 与 DDR 地址转换、别名。
4. DDR 参数 row14/col10/bank3/rank1/dq16 推算参考容量 256 MiB；这没有核实实物 DDR。BSP 的大地址窗口不能用于证明物理容量。
5. DDR AXI 为 128 位；顶层互连 ID 线为 8 位而 DDR 参数 ID 为 4 位，必须审查截断和响应路由。`apb_paddr` 等连接不能当作已可用的控制页，现有顶层未给出完成的外设连接。
6. 视频帧缓存自身已有像素/显示时钟到 `core_clk` 的跨域接口。应接它导出的 AXI 侧；不能用逐位同步替代整个 AXI CDC。

## 候选内存图

以下仅是共同线性字节地址图的候选，尚未建立 CPU 地址到 DDR 地址的转换关系。`memory_plan.json` 显式禁用，原固件、linker、视频顶层均未改写为这些地址。

| 区域 | 起点 | 结束地址（不含） | 长度 |
|---|---|---|---|
| 现有 CPU linker | 0x00001000 | 0x08001000 | 128 MiB |
| 视频候选预留 | 0x08010000 | 0x09010000 | 16 MiB |
| 共享候选预留 | 0x09010000 | 0x09020000 | 64 KiB |

共享图像槽相对偏移继续使用 v1 的 `0x1000`/`0x4000`，各 9216 字节。仿真 `shared_base=0` 只是 256 KiB 存储模型内部的测试地址；不能据此在板上把共享基址设成 0。

控制状态和描述符当前保存在 RTL 寄存器中，**没有自动镜像到共享区 0x0000**。温度图/环境快照预留区也尚未由本模块实现。CPU 不得直接把 DDR 内容强制转换为 `coop_pool_t`，再与硬件管理器同时修改状态。

## A 的视频接口

顶层 `c2_system_boundary` 的 `video_clk` 域使用以下严格顺序；所有 valid 在 ready 之前保持，数据在 valid && !ready 时不变：

1. A 先获得一张稳定、完整的 96×96 GRAY8 图；提交 `v_frame_valid`、`v_descriptor[511:0]`、`shared_base`。首字为 ABI `0x10000`，帧号在第 1 个 uint32，源 SOF 时间在第 2 个。相对布局与 `cooperation_v1.h` 的 64 字节描述符一致。
2. 等 `v_grant_valid`，核对 `v_grant_frame_id` 后用 `v_grant_ready` 接收授权。只有被授权后才发送像素。槽满或请求格式无效时返回事件，没有授权，也不发送像素。
3. 经 `v_word_valid/ready/data` **恰好发送 576 个 128 位字**。每字 byte0 位于 `[7:0]`，依次到 byte15 `[127:120]`，全图逐行从左上开始，无行间空洞。FIFO 只有 16 字、256 字节，必须响应背压。
4. 等 `v_event_valid`，读取 status/slot/generation/descriptor，再给 `v_event_ready`。完成一个事件后再提交下一候选帧。成功事件的描述符已填入槽、固定格式、长度、步长、完整标志及硬件 FNV。

描述符由 mailbox 传完整快照，像素由异步 FIFO 传输，授权和完成事件各有独立 mailbox。写帧开始与授权进入 mailbox 在同一个内存时钟握手，不会出现未启动写入却授权像素的情况。

**真实 MIPI 不能因这里的 ready 拉低而暂停。** A 应实现独立缩略图快照缓存/调度，主采集与 HDMI 持续运行。当前未提供这个视频侧整帧缓存，也没有把运动网格直接接入本模块。96×54 补边只是候选：桌面样图出现过分类翻转，最终缩放/裁剪仍待 A/C 使用真实画面确认。

写响应失败后，本模块不再发出该帧的后续 DDR 写，而是排空该帧剩余像素，之后 ABORT 并返回错误。发送者仍须交完被授权的 576 字；半帧断流没有自动超时/取消协议，需共同复位恢复。不得在收到错误后把旧帧剩余字当作下一帧发送。

## C 的 CPU 控制接口

当前是 `mem_clk` 域 ready/valid 接口，尚未映射到 APB 地址。CPU 时钟不同需总线桥/CDC；不能把 225 MHz CPU 控制脉冲直接连到内存域。此处控制命令码不是现有 C API 的负数错误码。

| CPU cmd | 行为 | 参数 |
|---|---|---|
| 5 QUERY | 返回当前槽 token 和描述符，不改变所有权 | slot；忽略输入 generation |
| 3 ACQUIRE | READY → READING | slot + 匹配的 generation |
| 4 RELEASE | READING → FREE | slot + 匹配的 generation |

响应包括 `cpu_rsp_status`、`cpu_rsp_slot`、`cpu_rsp_generation`、`cpu_descriptor`。`slot_states[1:0]` 是槽0、`[3:2]` 是槽1；FREE0/WRITING1/READY2/READING3。status：OK0、BUSY1、ESTATE2、EINVAL3；视频事件另有 WRITE_ERROR4。CPU 的 ALLOC/COMMIT/ABORT 被拒绝，避免软件绕过写完成屏障。

建议 CPU 查询 READY 槽、读取 token、ACQUIRE 成功后按 `shared_base+data_offset` 访问图像；成功 ACQUIRE 后只读图像，处理结束再 RELEASE。QUERY 只是快照，状态可能变化，必须检查 ACQUIRE 返回。桥接层未来把正数硬件状态转换成 `COOP_*` 软件返回值。现有 C4 PC 桥接使用软件池；它还未替换为本硬件后端，不可在板上同时运行两套所有权服务。

所有权顺序为 FREE→WRITING→READY→READING→FREE；忙时丢新候选、不覆盖旧槽。generation 每次 ALLOC 加一；旧代数/重复释放拒绝。generation 32 位回绕，禁止句柄跨越同槽 2^32 次复用仍被使用。reset 后 CPU 必须丢弃所有旧 token。

写完成屏障在最后一拍 W 之后仍等待 B：正常完整图 36 个突发、576 拍全部返回后才允许 COMMIT。描述符字段错误即使像素已写完也不会 READY。B 错误后 ABORT。CPU 缓存尚未处理：需证明共享区不缓存，或实现真实核的 clean/invalidate 与内存屏障后才能接 DMA；`volatile` 或单独 `fence` 不足以证明一致性。

## 总线与复位约束

`s_*` 打包数组按下标0/1/2分别预留 CPU/TinyML/视频，位切片为 `i*WIDTH +: WIDTH`；内部图像 writer 是第3源。它们必须已经处于 `mem_clk` 域。`m_*` 是唯一 DDR 事务出口，真实集成只保留一个经过配置的 DDR 控制器和 PHY。

当前可移植仲裁器只支持 **128 位完整拍、16 字节对齐、INCR、每突发不跨 4 KiB、无 ID**；允许 WSTRB 屏蔽字节。全局最多一个未完成突发，按主设备/读写请求轮询，无重排/窄访问/独占。不能把它直接替换厂家互连，也不能丢掉厂家 CPU/TinyML 的 ID/sideband 后宣称兼容。下一步优先保留厂家互连做完整适配，或按真实源接口扩展并重新验证本仲裁器。

`protocol_error` 对未对齐、越页、LAST 错误置 sticky 标志，但没有地址防火墙/隔离，也不自动中止违规访问。有限等待依赖合法主设备和 DDR 最终给出数据/响应；没有失联超时。仿真轮询通过不等于实时视频带宽通过。图像 writer 每字用16周期计算 FNV，会延长持有突发的时间，仍须用真实流量验证显示不欠载。

`arst_n` 共同异步复位 mailbox/FIFO/所有权/写入/仲裁。各域释放经过两级同步；禁止单侧复位。复位时所有访问者及实际 DDR 接口须协调取消未完成事务，待时钟稳定、DDR 校准完成再释放业务。DDR 数据不清零，但旧槽不再有效；测试特意保留部分写入数据来检查复位后不发布旧帧。物理 CDC 仍需验证 mailbox bundled-data 延迟、Gray 总线偏斜、同步器与 RAM 映射，不能用仿真代替亚稳态分析。

## 下一步合入顺序

1. A/C 对照真实 AXI 接口，确认 CPU/TinyML/视频的地址、位宽、ID、burst/size、缓存、时钟和复位；落实地址重定位及别名测试。先保留唯一 DDR，完成完整适配。
2. C 加入 APB 控制页和 CPU 驱动，将 QUERY/ACQUIRE/RELEASE 及回复快照接入固件；实现缓存策略，替换 C4 的软件池后端。APB 基址目前未分配。
3. A 加入可背压的灰度快照缓存，接授权/完整576字/事件协议，确认预处理与源 SOF 时间。统一毫秒源属于 C3 后续工作，本轮仅透传 timestamp。
4. 在独立整机工程内接厂家 DDR/SoC/视频 IP，综合并布局布线；补物理 CDC 和资源时序验收。
5. 有板后先 CPU 保留区读写，再加入连续视频/AI 并发、错误/复位/长稳及吞吐测试。C1 静态推理仍需单独真实 UART 证据。

本文件为 C 提供的实现接口和接入任务，没有代替 A/B 确认，也未向任何队友发送消息。
