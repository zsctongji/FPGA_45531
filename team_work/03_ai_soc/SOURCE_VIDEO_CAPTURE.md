# A 源像素采样接入与首像素时间戳

2026-10-25。本次接入 A 的 `video_a_capture`，将公共时间在源帧首个有效 DE 像素处锁存，完整传递到 C2 帧描述符。验证使用合成 GRAY8 视频帧、实际 A/C2 RTL 和 DDR 行为模型；没有连接物理摄像头、下载板卡或生成整机配置文件。

## 当前连接

```text
源像素时钟域：GRAY8 + VS + DE
  → c2_a_video_source
    → 原样保留的 video_a_capture / video_grid_sampler
    → 原样保留的 ai_frame_mailbox（双BRAM/读租约）
    → 既有C2搬运桥 / 异步FIFO / 源端完成确认
  → C2图像写入 / 唯一DDR出口
  → APB描述符 / CPU AXI读回 / 私有图像
  → 桌面模型对照
```

新增实现为 `projects/06_soc_c2/rtl/c2_a_video_source.sv`。A 的三个源码快照未修改，与之前交接版本逐字节一致。新接口文档原样保存于 `team_work/shared/a_interface_v1.md`，来源为远端提交 `0e8a5d73ee96e3e4753ef6087442e923f2e4413e`；没有解压或覆盖 A 的旧整库归档。

## native 顶层端口变化

`tools/prepare_c2_vendor.py` 生成的 `integration/c2_tinyml_soc_top.v` 已实例化新包装模块。

| 端口 | 含义 |
|---|---|
| c2_video_clk | 摄像头源像素时钟，不应直接用HDMI读出时钟冒充采集时钟 |
| c2_pixel_vs | 高有效，在消隐区上升的源帧边界 |
| c2_pixel_de | 高有效的源有效像素标志，每拍一个像素 |
| c2_pixel_gray[7:0] | 与DE同拍对齐的unsigned GRAY8 |
| c2_shared_video_ms/valid | 从唯一APB毫秒计数器跨域接收的完整快照 |
| c2_capture_config_valid | 参数能产生96×54网格时为1；错误配置禁止采集和图像请求 |
| c2_capture_record_* | 视频域中的完整源帧记录脉冲、完成标志、帧号、时间及宽高 |
| c2_capture_source_frames/format_errors | VS边界数量及物理帧格式错误计数 |

原来的外部 `c2_sample_valid/sof/eof/abort/gray/frame_id` 入口已经移除，避免绕过采样器或由外部重新填写帧号/时间戳。内存控制接口保持 **APB v2.2（0x00020002）**，图像描述符 ABI 保持 v1。

硬件默认几何参数为 `C2_FRAME_WIDTH=1920`、`C2_FRAME_HEIGHT=1080`、`C2_STEP_X=20`、`C2_STEP_Y=20`，对应A的96×54网格。参数只允许最终产生96×54网格，源宽高在1..65535内；不支持的组合将 `capture_config_valid` 拉低。比如1280×720配20×20步长不符合该接口，不能直接套用。本轮另用384×216、步长4×4缩短故障专项仿真，输出AI尺寸仍相同。

真实 MIPI 解包、多像素并行到单像素的适配、RAW/Bayer/RGB转灰度位于该接口上游，仍须由A/C按厂家视频工程接入。灰度处理若有流水延迟，VS/DE必须同步对齐。HDMI与完整视频帧缓存、板级引脚和时钟/DDR物理约束仍待整合。

## 首像素与延迟 EOF

公共时间源仍是C2/C3唯一的APB毫秒计数器，视频接收完整快照。首个快照有效前，采样器保持复位；恢复后等待源VS，之前没有合法帧边界的DE像素不会制造完整帧。共同复位会清除源采集状态、A缓存、CDC及C2槽状态，仍不支持单侧复位。

`video_a_capture.now_ms` 接公共视频时间。它在首个源有效DE像素锁存时间，并把 `sample_timestamp_ms` 随网格送给A mailbox；C2不再在注册后的网格SOF处改写为当前时间。

A采样器保留最后一个网格像素，直到下一VS确认整幅源帧尺寸正确，才输出EOF。在这拍，sample的帧号/时间仍属于上一帧；新的VS已开始下一帧编号。包装模块不改写这一时序，也不把VS时间当成首像素时间。

专项测试故意让公共时间快照恰好在首DE边界更新：首像素锁存 `0xFFFFFFFC`，注册的网格SOF已经观察到 `0xFFFFFFFD`。记录、DDR发布事件和APB描述符必须保留前者；帧完成时计数还会发生自然回绕。

`c2_capture_record_*` 是源视频时钟域的脉冲/快照，后续接CPU寄存器或其他时钟域时仍须完整跨域；不能逐位直连。`source_frames` 是VS边界计数，不等于完整帧数或AI推理次数。

## 验证入口

运行根目录 `19_test_video_capture.cmd`：先做完整C2回归，再把全帧链路的仿真DDR读回图送入桌面参考模型。

- `tools/prepare_c2_video_test.py` 从既有AXI/DDR/APB组合测试生成 `sim/tb_c2_video.sv`，替换直接网格输入为完整VS/DE/GRAY8像素。
- 1920×1080、20×20步长：逐像素输入完整源帧，检查下一VS前不提交、完整9216字节、FNV、延迟EOF、首DE时间、计时回绕、APB元数据和CPU AXI读回。
- 两组384×216、4×4步长及时钟比：连续两帧与搬运重叠、双槽占满时丢新AI帧、短行/少行/多行拒绝、恢复后新帧、后台三路读写并发、源帧中途共同复位。
- `sim/tb_c2_video_config.sv` 检查不支持的网格配置不会生成采集帧或DDR请求。
- 汇总为 `logs/c2_selftest.json`。测试时钟分频及初始计数只用于加速/回绕注入，不构成板上频率或带宽测量。

实际仿真DDR字节保存到 `build/c2/a_c2_video_frame0.gray`，配套JSON记录源几何、帧号、首DE时间、网格SOF观察时间和EOF时公共时间。首帧图案设计为与既有C24自检输入相同，原图FNV为 `e8113185`。

`python tools/check_a_c2_pc.py --video-capture` 检查当前三个源像素回归用例均通过、元数据与原图相符，再做桌面推理对照。结果在 `logs/a_c2_video_pc_inference.json`，记录当前RTL报告及输入元数据哈希。它仍使用已审计的桌面元数据兼容模型，不证明与板上旧TFLM/加速器逐值等价，也不是相机准确率测试。

`tools/verify_c24_package.py` 同时核对原网格测试、新全帧测试、新native综合、桌面结果及原C24 CPU固件。CPU软件和APB布局未修改，因此沿用 `c24-d1fc40db3541b41f`；默认仍关闭实时MMIO。旧C1 FPGA配置不包含这里的新硬件。

本轮最终证据：

- `logs/c2_selftest.json`：46次RTL运行、主机驱动及RV32对象检查PASS；包括一个完整1920×1080源帧用例、两组压缩几何的故障/连续帧用例及错误配置保护。
- `logs/a_c2_video_pc_inference.json`：全帧采样后的实际仿真DDR读回图与直接输入的桌面推理一致，原图/张量FNV分别为 `e8113185` / `8f0f8585`，输入字节与原C24合成自检一致。
- `logs/c2_native_synthesis.json`：新native map PASS，34160 LUT4、30789 FF、51 DSP48。A/厂家存量告警记录在 `logs/c2_native_warning_review.json`，未声明全部消除。
- `logs/c24_package_check.json`：678项源码/产物/报告身份检查PASS。原C1的527项检查保持PASS。

综合重建入口为 `15_synth_c2_native.cmd`；这仍是map流程，不包含物理MIPI/HDMI接入、P&R、最终时序或可下载整机配置。

## 后续接线边界

A提供真实源时钟域的单像素GRAY8/VS/DE及已确认的几何/极性；B核对实际PCB、DDR和引脚；C继续接入同一DDR体系并整理物理约束。真实摄像头、完整视频/HDMI、物理地址/缓存、时序和板上推理仍待验收。源像素接口阶段的源码与离线证据通过GitHub协作仓库交接。
