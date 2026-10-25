# C2/C3 统一时间与 C24 验收工具

2026-10-25。主工程为 `C:\Users\16034\Downloads\FPGA\FPGA_2026_T3_P3`。本次只完成电脑端实现、仿真、构建及逻辑综合，没有打开板卡串口或下载固件。

## 单一时间来源

`projects/06_soc_c2/rtl/c2_shared_time.sv` 在 **100 MHz APB 外围时钟域**产生唯一的 32 位毫秒计数。每 100000 个有效时钟递增一次；共同复位清零，约 49.7 天自然回绕。所有比较窗口小于 2^31 ms。

- CPU/C3：从 C2 APB 读取该计数，不再另起传感器毫秒计数器。
- 视频：通过 `c2_cdc_mailbox` 持续接收同一个计数的完整快照。源端保持 32 位数据，直到目标接收并回传确认；不逐位同步自由变化的二进制总线。这替换了原接口文档中尚未实现的 Gray 分发提案。
- C1：保留原 CLINT 静态诊断固件和产物；其时间不用于整机传感器/图像对齐。C24 合成自检的耗时仍用 CLINT ticks，现场帧时效和推理起止则使用公共 APB 时间。

快照有传播延迟，并非两个时钟域在每一拍都显示相同数值。连续时钟下可按保守的 `8×APB周期 + 8×视频周期` 预算传播延迟，再加毫秒量化误差；最终须按真实频率和布局布线确认。该设计不支持独立复位或暂停时钟后继续沿用旧的有效标志。复位必须同时覆盖 CPU、时间服务、视频桥、CDC 和槽所有权。

首个快照到达前 `shared_video_valid=0`。native 副本在此期间禁止样本进入 A 缓存并中止残帧，避免把复位值当成有效采集时间。

当前 native 的时间戳锁存点明确为 **`sample_valid && sample_sof`，即 96×54 网格的首个样本**；A mailbox 会将这个值与整帧元数据一起保存。顶层不再接受独立的 `c2_sample_timestamp_ms`。输出 `c2_shared_video_ms/valid` 可供后续 A 视频模块和运动元数据使用。

这不是 VS 边沿，也没有沿用 A 原 `video_a_capture` 在首个有效 DE 锁存的旧时间。真实视频整合时 A/C 须统一原始帧 SOF、首个有效 DE 与首个网格样本的定义，测量偏差并决定最终采集锁存点；不能把本轮合成网格时间称为真实相机 SOF 实测。A 原源码副本未修改。

## APB v2.2，必须配套固件

图像描述符 ABI 仍为 `0x00010000`；C2 控制传输版本变为 **`0x00020002`**。旧 v2.0/v2.1 固件与新硬件不得混用。

| 偏移 | 寄存器 | 只读含义 |
|---|---|---|
| 0x80 | CAPABILITIES | bit0=RX只读；bit1=源端完成确认；bit2=公共时间；native 值为 7 |
| 0x84 | TIME_MS | 公共 uint32 毫秒计数，CPU 原子读取一个字 |
| 0x88 | TIME_STATUS | bit0=时间服务已完成源域复位释放，其余位为0 |
| 0x8c | TIME_HZ | 计数器输入时钟，正式构建为 100000000 Hz |
| 0x90 | TIME_KIND | 1=公共 APB 毫秒计数器 |

时间寄存器不依赖 DDR `map_enable`，但访问前仍必须确认真实 APB 地址；尚未核实的板卡不能试读候选 MMIO。测试台可加速分频并从临近回绕值启动，native 固定使用默认 100 MHz、初始0。

## C3 给 B 的调用入口

新增 `c3_hal/c3_shared_time.{h,c}`，使用可报告失败的 API：

```c
c3_shared_clock_t clock;
/* io 必须是已核实 APB 映射的 C2 访问后端，并保持有效。 */
int rc = c3_shared_time_bind(&clock, &io);
uint32_t timestamp_ms;
if (rc == COOP_OK) rc = c3_shared_now_ms(&clock, &timestamp_ms);
/* 只有 rc==COOP_OK 才能给完整有效的传感器样本加时间戳。 */
```

绑定校验 ID、APB版本、公共时间能力、时钟频率及来源。读取前后检查 TIME_STATUS；未就绪返回 EBUSY，读失败返回错误，输出变量不被失败调用覆盖。0 毫秒是合法值。不能在失败时退回另一个独立时钟或发布有效传感器样本。

原 `c3_now_ms`/CLINT、I2C/GPIO HAL 保留，用于 C1 和已有测试。**整机传感器时间改用 `c3_shared_now_ms`**；不要用旧 CLINT 回调混合对齐。I2C/GPIO 的真实硬件后端仍未完成，本次没有新增传感器实测。

## C24 固件日志协议

默认合成自检顺序：

```text
BOOT → MODEL → SELFTEST_BEGIN → SELFTEST → LIVE_DISABLED → DONE
```

BOOT 记录构建版本、输入策略、三个构建开关、APB版本和CLINT频率。MODEL 记录模型FNV。自检开始/完成记录原图和张量FNV、synthetic=1，完成记录原始INT8分值、显示分值和耗时ticks。卡在模型初始化/Invoke 或截断日志会缺少后续记录，验收失败。

现场构建在自检后输出 LIVE_READY，包含公共时间类型/频率/能力。每次真实调用推理输出：

```text
INFER_BEGIN(sequence) → INFER_END(sequence,status) → FRAME(sequence,...)
```

厂家MicroPrintf每次最多256字节，FRAME使用两次受限长度输出拼成一行，只有后半段换行；最大uint32数值已用实际厂家格式化器验证。FRAME 保留帧号、源时间、CPU收到/推理开始/结束时间、原图/张量FNV、原始分值及有效状态。错误帧输出无效；已取得图像后若公共时间未就绪，会记录无效帧，不会被当成空槽而静默跳过。推理起止倒退也会拒绝结果；传输服务污染则输出 FAIL 要求共同复位。现场路径使用 `c3_shared_now_ms`，不再拿 CLINT 与视频时间直接相减。

默认 `16_build_c24.cmd` 仍关闭现场MMIO。只有物理映射和公共时间经过实物验证后，才使用原有 `--enable-live --verified-map --verified-shared-time` 参数重建；这几个开关是调用者的验收声明，不能代替测试。

## 到板后采集与检查

板卡到手并确认配套 FPGA/CPU 文件与串口后，运行（替换 COM实际端口）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/capture_c24_uart.ps1 -Port COM实际端口 -Seconds 180 -BoardPortConfirmed
```

采集为115200 8N1，不发送串口命令；DTR/RTS关闭。逐段写盘，并在 `logs/c24/` 保存日志、当次固件清单副本及哈希/捕获元数据。`ExecutionPolicy Bypass` 只作用于此次进程，不修改系统策略。一个日志只捕获一次启动。

使用采集时保存的清单，而不是以后重建覆盖的当前清单：

```powershell
python tools/check_c24_uart.py logs/c24/uart_实际时间.log --manifest logs/c24/uart_实际时间.manifest.json --output logs/c24/selftest_validation.json
```

可加 `--reference logs/a_c2_pc_inference.json` 严格比较合成自检的原始INT8。当前桌面模型是已审计的元数据兼容副本，尚未证明与板上旧 TFLM/加速器逐值相同；若不一致，保留失败记录诊断，不自动放宽误差。

真实现场构建用对应现场清单检查：

```powershell
python tools/check_c24_uart.py logs/c24/uart_实际时间.log --manifest logs/c24/uart_实际时间.manifest.json --mode live --min-frames 3 --output logs/c24/live_validation.json
```

支持 `--frame-dir <已保存原图目录>`：目录中提供每个有效帧的 `frame_<帧号>.gray`（无头9216字节），工具重新计算原图和量化张量FNV。缺失或不匹配会失败；未提供时报告 `live_input_bytes_verified=false`。这些图像仍须另外证明实际采集来源。

检查拒绝版本/模型/输入不符、重复字段/启动、非法分值、错误映射、缺失推理结束、重复/倒序帧、未来/过期时间、时间倒退、无效帧及固件 FAIL；支持帧号与毫秒自然回绕。现场采集若恰好截在一次推理中间会失败，应保留该记录并重新采集完整窗口。

**检查器 PASS 只代表日志一致性。** `board_inference_passed/live_camera_passed/preprocess_policy_approved` 不会因格式检查自动变为 true；实物下载、采集来源、桌面对照和准确性评估分别保留证据。

## 电脑端验证

- `18_test_time_c24.cmd`：42次C2 RTL回归及主机/RV32检查，然后运行C24验收工具测试。
- `tools/test_c24_acceptance.py`：38个合成日志/CLI单元测试、实际厂家格式化器的最大数值日志检查、采集脚本语法、打开串口前的端口确认检查；不打开串口。
- `tools/build_c2_host.cmd`：驱动/联合流程断言（含时间未就绪与倒退的拒绝路径），以及23项公共时间后端检查。
- `tools/verify_c24_package.py`：当前固件、源码、42次RTL报告、native综合、桌面读回和验收工具的配套身份检查。
- `logs/c2_native_synthesis.json`：新版native map PASS，33664 LUT4、30351 FF、51 DSP48；未完成布局布线、物理CDC和板上验收。

新时间测试覆盖三组异步时钟比、精确分频、只读APB、计数回绕、共同复位与在途快照清除。A→C2测试同时检查SOF锁存的时间随完整帧传递。

当前配套版本为 `c24-d1fc40db3541b41f`，BIN为1386864字节，119个编译单元链接成功。最终记录：42次RTL回归、29702项主机驱动/联合流程断言、23项公共时间后端检查、38个日志/CLI测试和实际厂家格式化器测试通过；666项配套身份检查PASS。C1原包527项检查保持PASS。详见 `logs/c2_selftest.json`、`logs/firmware_c24.json`、`logs/c24_acceptance_tests.json`、`logs/c24_package_check.json`。

真实视频/DDR映射、外设接线、时钟频率、最终时序和板上推理仍待验收；本次源码、配套CPU固件和离线验收记录纳入GitHub协作交接。
