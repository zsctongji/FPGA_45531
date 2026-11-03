# C9 真实视频帧格式观测（2026-11-02）

状态：首轮实板几何观测已完成，后续 CSI 探针的电脑端构建与审计也已完成，等待新一轮实板采集；真实视频验收仍未通过。当前正式诊断入口继续使用 `config/c9_active_profile.json` 的 display 镜像。本轮不改 DDR 参数、校准算法、验收条件、1920×1080 常量或坏帧拒绝规则，不写 Flash。

## 已确认的边界

实板原始日志 `logs/ram_diagnostic_20261101/20261102_195114/uart.log` 显示：共享时间检查通过，摄像头寄存器回读 1920×1080、ID cd6b；20 秒窗口 505 次源帧边界、504 次格式错误、0 次 AI 完成，最终 `live_frames` 失败。该证据不能解释实际信号波形，也不能算出有效帧数。

新增本地实验使用现有 `physical_pixel_split`、实际 A 的未加密 ISP 和真实 `video_a_capture`，没有替换为行为模型：

- 连续输入：32×8 三帧的逐行/整帧计数通过。
- 行内 valid 间隙输入：保持每行总像素数和 HS，ISP 输出出现 16 像素 DE 段，而接口要求连续 32 像素，稳定触发 `ISP line split/length`。
- 真实 capture 边界：32×8 正常帧、16×16 断续段、24×8 裁剪帧、32×7 缺行、范围饱和、复位和原 flags 透传均按预期观测或拒绝。

命令：`C:/Python311/python.exe -X utf8 tools/test_c9_camera_geometry.py`。记录 `logs/c9_camera_geometry_tests_20261102.json`；其中 expected rejection 是合成间隙的反例，不是摄像头的实测结论。

排查顺序：真实 CSI valid 在 HS 内不连续；ISP/串并转换改变行连续性；实际有效尺寸或像素打包不匹配。只有接板记录才能在这些可能之间继续判断。

## 只读观测镜像

`build/c9_camera_geometry_image_20261102` 从已通过实板图案 DMA 的 display 镜像隔离复制。唯一功能增量是把现有 capture 的 `record_width/height/complete/valid` 接到同一 video_clk 域的只读标志；像素路径、控制寄存器、复位、CDC 队列、DDR、引脚和时钟均不改变。

在该镜像中，视频快照 bank=1、pair=3 的 hi（source_flags）定义：

| 位 | 含义 |
|---|---|
| 31:20 | 最近记录的最大连续 DE 段宽度，超过 4095 饱和 |
| 19:8 | 最近记录的 DE 段数量，超过 4095 饱和 |
| 7 | 本次复位后已产生 capture 记录 |
| 6 | 原 capture 的 record_complete |
| 5 | 宽度发生饱和 |
| 4 | 高度发生饱和 |
| 3:0 | 原 RUN / pattern_mode / pattern_busy / fault，不变 |

尺寸来自可能被拒绝的上一帧；“段数量”不一定等于传感器 HS 行数。该 32 位值由原有快照邮箱一致采样；其他 pair/时钟域不保证同一瞬间。该扩展仅适用于固定 SHA 的 geometry 镜像，不能用来解释历史 display/nopack 日志。

构建与审计入口：

```powershell
C:/Python311/python.exe -X utf8 tools/prepare_c9_camera_geometry.py
C:/Python311/python.exe -X utf8 tools/prepare_c9_geometry_capture.py
& tools/run_c9_camera_geometry.ps1
C:/Python311/python.exe -X utf8 tools/audit_c9_camera_geometry.py
C:/Python311/python.exe -X utf8 tools/report_c9_camera_geometry.py
```

生成器拒绝覆盖已存在实验目录。复现时应先保留已有证据，在新的隔离路径创建下一版实验，不直接覆盖已审计版本。

## 小固件与实板入口

`firmware/c9_camera_geometry/c9_geometry.bin` 为 3508 字节，不含模型。运行前沿用六位置、24 word 的 DDR 映射检查，记录 before 快照，单次提交 camera RUN，等待 10 秒，记录 after 快照。`DONE mode=geometry` 只表示采集结束，不表示视频或 TinyML 验收通过。

`tools/check_c9_geometry.py` 核对固定镜像、固件完整回读、版本、快照序号和协议，输出 `CAPTURED_GEOMETRY_ONLY`。解析器的六项合成测试见 `logs/c9_geometry_decode_tests_20261102.json`，无法替代实板证据。

```powershell
# 默认仅核对本地身份，不接触 USB 或串口
C:/Python311/python.exe -X utf8 tools/run_c9_geometry.py

# 接板后：先读 USER2 校准状态，采集 camera 几何，最后恢复 C10
C:/Python311/python.exe -X utf8 tools/run_c9_geometry.py --capture --port COM13
```

脚本自行调用绑定的 Efinity SDK Python，保存尝试目录与原始日志；校准仍用既有严格检查器。摄像头诊断完成或失败后均尝试恢复 C10 并检查六组静态推理。未连接板卡时不要运行 `--capture`。

实测后先看 width/height、complete、format_errors、overflow、fault，再决定下一次在哪个 CSI/ISP 边界增加观测或规范化输出。不得仅因为段数量异常就忽略 DE、拼接未知像素、放宽坏帧判定或更改预期尺寸。无新增实板证据前，不推广为 active profile，不声称真实视频、最终整机或冷启动通过。

## 实板结果与暂停点

geometry 位流 SHA256 `0f6285a20a6f1352ea578b09ec37d588c62af3e3c52737c47fd34b33064c3293`；60582/60800 XLR，RAM224、DSP60，setup +0.115 ns、hold +0.026 ns，66 位 Gray CDC 两角通过。STA 首次启动曾报 Windows 拒绝访问，原失败日志保留于构建目录 `sta_launch_rejected`，相同命令重试通过。

`logs/ram_diagnostic_20261101/20261102_205853/geometry_observation.json`：252 次源帧边界、251 次格式错误，最近一帧最大连续 DE 段宽 72 像素，段数量饱和 4095（实际超过该值）、complete=0、overflow=0、AI 完成=0；状态 `CAPTURED_GEOMETRY_ONLY`。不能把这条诊断采集当作真实视频通过。DDR USER2 校准另存 `20261102_205809`，CPU 固件完整 3508 字节回读一致。

诊断结束后 C10 恢复与六组静态推理通过，记录 `logs/c10_warm_boot_20261101/20261102_205918/attempt.json`。整个过程未写 Flash，正式 active profile 仍为 display。

后续只读 CSI 探针保留现有捕获几何，在原 CSI 像素时钟域测量最后一条非空 HS 的 payload 组数和 valid 段数；phy bank 的 hi 定义为：31:22 groups、21:12 runs、11 seen、10 clipped、9 valid_outside_hs、8:1 保留零、0 原 camera_fault。对应 `c9_phy_geometry.sv`，专项仿真通过。该镜像的 bank4 hi 不再适用于旧摄像头验收器，须使用固定镜像对应的 `check_c9_phy_geometry.py`，只输出诊断观察结论。

构建目录 `build/c9_phy_geometry_image_20261102` 当前未完成综合/P&R/STA，已按用户要求中止。该轮首次准备脚本路径错误已及时中止并修正，失败准备目录完整保留于 `c9_phy_geometry_image_20261102_prepare_rejected`；既有 display、geometry 审计身份复核通过。随后 Interface Designer 的 `efx_pgm --query_bitstreams` 子进程曾停滞，终止该查询后 interface 通过。没有在板卡加载这轮未完成探针。

恢复顺序：检查新 runner 的目标目录，运行 `tools/run_c9_phy_geometry.ps1` 完整构建，再运行 `tools/audit_c9_phy_geometry.py`。只有审计通过才能运行 `tools/run_c9_phy_geometry.py --capture --port COM13`。若工具再次停滞，保留日志定位原因；不放宽 DDR/STA/CDC 检查。实测后再决定视频适配修复，当前还没有改像素路径。

用户暂停时，新文件只保存在主项目本地，尚未同步本地交接仓库，未提交/推送 GitHub。

## 后续电脑端已完成

用户恢复了电脑端任务，CSI 探针已完成综合、P&R、STA 和 66 位 Gray CDC 两角审计，setup/hold +0.223/+0.026 ns；专项 RTL 与 11 项解码检查通过。位流及工具已打包，见 `C9_CSI_PC_READY_20261102.md`。本阶段未访问板卡，未写 Flash，未改变 active profile；本地交接副本已同步，未提交/推送 GitHub。前述“未完成构建/尚未同步”仅描述暂停时的历史状态。
