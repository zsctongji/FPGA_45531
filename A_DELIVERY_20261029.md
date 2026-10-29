# A 同学交付清单（2026-10-29）

交付范围：摄像头、HDMI显示接口、灰度/运动与图像交接、PC事件接收、验证和本人材料。当前板卡未连接，不进行新硬件测试。代码是A的增量交付，不能作为最终整机验收通过证明。

| 交付项 | 文件/入口 | 当前结果 |
|---|---|---|
| 彩色、灰度、运动红框、热力图演示 | 既有四类录像 | 用户确认均已录好；录像文件未接收审阅，无需重录 |
| 真实采集帧率与曝光修正 | projects/11_a_camera_diag；logs/a_camera_input_acceptance_20261029.json | SC431HAI、1920×1080、30.20124fps；65.196秒1970条连续完整帧；接屏亮度合适、物体清楚 |
| AI灰度输入与运动 | rtl/a_gray_snapshot.v、a_headless_uart.v；projects/12_a_headless；team_work/01_video/ai_samples_20261029 | 实际96×54+21+21=96×96、9216字节、SUM32、同帧运动字段；5张真图样本及手掌/图案响应 |
| HDMI结果显示接口 | rtl/video_a_result_display.v、a_status_guard.v、a_hdmi_display_exercise.v；projects/13_a_display_test | 六状态循环和真实视频持续由用户确认；始终A DISPLAY TEST，B/C字段是测试输入 |
| CPU读图适配 | firmware/a_side/a_side.c/.h；rtl/ai_frame_mailbox.v | 所有权、完整提交、忙时丢新帧；MSVC主机执行和RV32交叉编译通过；未做实际软核读图/推理 |
| PC UDP接收与保存 | tools/A_PC_receive.cmd；tools/a_side/receiver.py、protocol.py | CRC、乱序、重复、超时、会话隔离、同事件配图；300合成事件PC压力测试；真实板端网口闭环待联合 |
| 回归/构建/材料 | tools/A_selftest.cmd；logs/a_side_selftest.json；docs/A_开始这里.md；team_work/01_video/本人报告章节_A.md | 27项Python、12个RTL测试台及UART变体通过；13完整流程与最终setup/hold 0.318/0.026ns通过 |
| 长稳记录 | logs/a_delivery_status_20261029.json；logs/a_display_interrupted_audit_20261029.json | 最新1133.064秒、34221条连续源记录、985张完整图 |

## 本次下载内容

`A_video_source_20261029.zip` 保留项目目录结构，包含A的RTL、C适配、Python/PowerShell/CMD工具、仿真、11/12/13工程源码、对应bit、5张真图、显示预览和关键测试记录。`A_video_source_20261029.sha256.txt` 用于核对整个压缩包；包内MANIFEST.json列出每个文件的字节数/SHA256与验收边界。

解压后先阅读 `docs/A_开始这里.md`；把增量接入已有协作工程前，先比较同名文件。仓库的codex/team-handoff已有C2/C24共享DDR、时间和视频缓存软件更新，本A实物诊断尚未与该版联合上板；保留C的软件进展，不能把本地旧副本覆盖回去。

本包不含Efinity安装包、许可证、Python运行时、全量原始串口长日志和已有录像。大体积原始记录保留本机，审计文件保留其SHA256。编译需要原厂工具/对应IP环境；离线测试需要Python3.11+与Icarus，串口采集需要pyserial，PNG回放需要Pillow。

## 还需联合完成

1. C与A：把真实CSI源帧ID/共享时间随DDR银行传递，实际软核取得完整当前图并输出SUM32与推理日志，视频保持连续。
2. B/C与A：接当前热图、温湿度、AI/融合、报警保持和预测点，验收真实同屏；13测试固定值不带入最终工程。
3. B/C与A：经网线发送真实事件及同帧缩略图，A保存PC接收结果。
4. 重新连接板卡后复测至少30分钟不中断；当前不把18.9分钟或此前24.3分钟拼成30分钟。

## 版本与接线边界

最近上板13：Ti60 ID 0x10660A79，USERCODE 0x41354431，bit SHA256 d66cc97a2919a95ae21c556297dfd4736645d4b9024b2775682a75c748d181a3。FT4232 C最近为COM30/921600，重插后可能变更。当前已断开，不能声称仍在运行该临时镜像。

11/12/13保持J28.37/39为输入、J28.38蜂鸣器低；未改接线、未写Flash。旧02/04/05驱动LCD引脚，与当前传感器接线冲突，不能带当前接线直接加载。A3帧号属于显示域，本地时间不是最终SoC共享时间；运动框是变化区域，不是AI人体框。
