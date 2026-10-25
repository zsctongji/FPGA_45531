# A→C2→TinyML 联调交接（2026-10-25）

后续源像素接入见 [SOURCE_VIDEO_CAPTURE.md](SOURCE_VIDEO_CAPTURE.md)：当前native输入为GRAY8/VS/DE，A采样器及首DE时间已经接入；下文网格输入为前阶段记录。

后续更新：统一APB时间、视频快照CDC、C3时间后端和C24验收工具已完成；当前为APB v2.2，42次RTL回归。请先读 [TIME_AND_C24_ACCEPTANCE.md](TIME_AND_C24_ACCEPTANCE.md)。下面v2.1、39次及旧timestamp传递方式是本轮前阶段记录，当前native以公共时间在sample_sof锁存；尚未替代真实相机SOF验收。

主工程：`C:\Users\16034\Downloads\FPGA\FPGA_2026_T3_P3`。本轮复用GitHub中A的代码（最近A提交06908f4），没有改写A的原模块、五个基线或C1固件。A源码副本及SHA位于 `projects/06_soc_c2/a_side/SOURCE_MANIFEST.json`。

## 本轮实现

```text
A 96×54 完整样本网格 → A BRAM双缓冲/读租约
 → 字节读取、补边检查、16字节打包、SUM32与FNV
 → C2跨时钟FIFO → 预攒完整突发/FNV → 唯一DDR出口
 → 源端完成确认 + 最后DDR写响应 + 帧号/FNV一致 → READY
 → APB取帧/缓存失效 → CPU私有GRAY8拷贝 → 释放DDR槽
 → pixel-128 → 厂家TFLM推理 → 原始INT8与0..255显示分值
```

- `rtl/c2_a_mailbox_bridge.sv`：租用A的源槽，接收C2授权后发送恰好576个128位字；低字节在低位。反压时保持数据和租约，C2回复后释放A槽。
- `rtl/c2_a_image_source.sv`：把A的原 `ai_frame_mailbox` 与搬运桥组合；输入为A采样器输出的sample_valid/SOF/EOF/abort/GRAY8/帧号/时间戳。
- `rtl/c2_source_fence.sv`：等待源端和DDR两种完成，校验帧号/FNV。单独收到DDR完成不会READY；源端错误也不会提交。
- `rtl/c2_image_writer.sv`：在发出AW前攒齐并校验一批（最多16拍）数据，写突发期间不因等待A的字节或计算FNV而占住DDR。
- `team_work/03_ai_soc/c24/c24_pipeline.c`：使用C2硬件所有权服务；私有拷贝完成并释放后才调用推理，拒绝过期/重复帧，保留原始INT8分值并输出 `person_u8=person_raw+128`。
- `team_work/03_ai_soc/c24/main.cc`：真实厂家TFLM模型的联合应用，包含合成自检及现场取帧路径。

读错误/读超时后，桥会把剩余流排成576个字，提交错误的源端确认，再释放A槽；填零的错误帧不会进入READY。BUSY回复不读取像素、不发送完成确认。共同复位取消两边租约、消息、打包状态和在途事务；不支持单侧复位。

A的BRAM槽号与C2的DDR槽号/generation互相独立，不能直接复用。当前桥独占A mailbox的reader端口；CPU推理和后续网络发送应使用已取得的私有图像或经过明确仲裁的其他读口，不能同时绕过桥去操作同一租约。

## 配套版本

图像描述符仍为 `COOP_ABI_VERSION=0x00010000`。APB控制版本升级为 **0x00020001（v2.1）**，避免联合程序误用不支持源端确认的旧控制页。

新增只读偏移 **0x80 CAPABILITIES**：bit0=RX只读接收，bit1=源端完成确认。新的native接入副本启用后读值为3；联合程序要求bit1。旧版0x00020000会在驱动初始化阶段被拒绝，不能混用固件和FPGA接口。

`REQUIRE_SOURCE_COMPLETION=1` 时，视频域增加 `v_source_valid/ready`、error、frame_id、fnv；该快照经过CDC，最终与DDR完成汇合。既有独立测试可用参数0保留原写完成流程；新native副本固定使用1，并实际实例化A搬运桥。

事件status=4现在表示传输失败，包含DDR失败、源端错误、帧号或FNV不一致；失败槽回FREE。A桥的source_faults可用于区分源端故障，仿真及native调试端口保留该计数。

## 输入策略与时间

本桥传输A当前的96×54网格，上下各21行黑边形成96×96。校验A的SUM32，同时对完整9216字节另算FNV；两种校验不混用。

该处理仍标为 **pad54_candidate**。此前桌面样图出现过补边导致类别翻转，不能写成已验收的摄像头模型预处理。真实采集的每拍像素数、抽样位置、源时钟及画面尺寸仍需A/C核对。

A当前timestamp锁存在VS后的首个有效DE。本轮原样传递，不把它悄悄改成VS边沿时间，也没有把独立计数器冒充共享时钟。现场程序仍要求统一时间来源经过验证；过期窗口为现有1000ms工程初值，需按板上实际推理耗时验收。

## 构建与运行入口

1. `13_test_c2.cmd`：目前39次RTL运行、主机驱动/联合流程测试和RV32对象检查。
2. `16_build_c24.cmd`：构建独立 `tinyml_c24` 应用，118个编译单元；生成 `firmware/c24_frame_person_detect/tinyml_c24.{elf,bin,hex,map}`。
3. `17_test_a_c2_pc.cmd`：上述RTL/主机测试后，把实际仿真DDR读回的图像送入桌面模型作对照。
4. `15_synth_c2_native.cmd`：生成并综合含A桥的厂家CPU/TinyML/单DDR接入副本。是map步骤，没有最终引脚/布局布线/可下载FPGA文件。
5. `python tools/verify_c24_package.py`：核对固件、当前源码、RTL/综合报告及读回图身份。

原工具链由本机安装提供，仓库不包含工具安装目录。新固件构建从厂家Makefile提取原始编译计划，再以Windows原生子进程执行，避开本机make启动GCC子进程时的路径问题；未修改Windows安全设置或原C1构建产物。

## 固件默认行为

默认运行已链接的真实TFLM模型，对与RTL读回图一致的**合成图案**执行静态自检，日志前缀 `C24|SELFTEST`、`synthetic=1`。之后打印 `C24|LIVE_DISABLED`，不访问C2共享区/MMIO。现场路径仍保留在ELF中，并检查四个关键入口已链接。

现场分支需要实际地址映射和共享时间都完成验证，再用 `python tools/build_c24.py --enable-live --verified-map --verified-shared-time --shared-base <已验证基址>` 重新构建。当前默认构建入口不启用这些选项；缺少验证标志会在构建前报错，不改变已有产物。标志是调用者提供的验收声明，不能代替物理映射测试。

原C1 FPGA配置只可作为静态TinyML基线，不能提供新版C2 APB/源端确认。现场取帧需要配套的新整机硬件、真实视频接线和最终约束。CPU HEX不能作为FPGA配置文件下载。本轮没有烧录Flash、生成整机Flash合并镜像或占用串口。

## 本轮证据

- `logs/c2_selftest.json`：39次RTL运行PASS，包含3种A/C时钟比、源端确认延迟、两种完成顺序、SUM错误、读错误/超时、坏补边、错误授权、BUSY、DDR错误、复位和释放。
- `logs/c2/host_driver_test.log`：20446项断言；检查私有拷贝、原始INT8映射、槽释放先于推理、时效/顺序/失败路径。推理回调为mock。
- `logs/a_c2_pc_inference.json`：真实仿真DDR读回与直接输入的桌面模型推理一致。合成图raw FNV=`e8113185`、tensor FNV=`8f0f8585`；原图SHA与固件自检图一致。桌面仍使用已审计的元数据兼容副本，没有改板上原模型或证明与旧TFLM逐值相同。
- `logs/firmware_c24.json`：ELF32 RV32IM，入口0x1000，BIN 1385472字节，小于4MiB引导拷贝上限；版本以C24_INPUT_MANIFEST.json为准，默认live_mmio_enabled=false。
- `logs/c2_native_synthesis.json`：含A桥的厂家接入副本Efinity map PASS；33882 LUT4、30222 FF、51 DSP48。范围不含实际MIPI/HDMI视频IP接入。
- `logs/c24_package_check.json`：644项源码/产物/报告身份检查PASS。原C1的527项检查保持PASS。

以上不能替代实体采集帧率、共享DDR/缓存一致性、最终时序或板上推理。下一步是接A真实采样/视频AXI、实现并确认统一时间和实际映射，再做整机布局布线及上板验收。

本轮更改通过GitHub协作仓库交接；最新APB v2.2、统一时间及验收工具说明见本文顶部链接。
