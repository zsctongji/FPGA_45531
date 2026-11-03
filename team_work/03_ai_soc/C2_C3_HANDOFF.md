# 给 A/B 的 C2/C3 交接入口

最新源像素接入见 [SOURCE_VIDEO_CAPTURE.md](SOURCE_VIDEO_CAPTURE.md)。当前native接A采样器，公共时间在首DE锁存；下文为历史交接。

当前增量：统一时间RTL和C3可报错的APB时间后端已实现；APB已为v2.2，旧版固件不得混用。B的整机时间调用 `c3_shared_time_bind/c3_shared_now_ms`；原CLINT回调仅保留独立基线。最新说明为 [TIME_AND_C24_ACCEPTANCE.md](TIME_AND_C24_ACCEPTANCE.md)，下方为之前交接记录，真实I2C/GPIO仍未实现。

日期：2026-10-24；当前文件夹为主开发来源，不是已经接线的整机。

本轮 C2 实现与测试已更新到 [C2_INTEGRATION.md](C2_INTEGRATION.md) 和 `projects/06_soc_c2`，运行 `13_test_c2.cmd`。已有单 DDR 事务出口、CDC/FIFO、图像写入及所有权服务的功能仿真；尚未接真实 SoC/IP、APB 和 CPU 缓存。

第二阶段更新见 [C2_VENDOR_APB_CACHE.md](C2_VENDOR_APB_CACHE.md)：现已实现厂家接口/ID/单拍窄访问适配、APB控制、RX只读缓存驱动和独立SoC接入副本。原软件ABI保持v1，APB传输ABI为v2。电脑回归34次，物理地址、真实视频、板上缓存与最终时序仍待验证。

给 A：
- 读取 ../shared/interface_contract_v1.md、../shared/include/cooperation_v1.h。
- 图像/帧元数据、GRAY8 校验、运动坐标、两槽所有权和丢帧策略已经固定。
- shared/src/cooperation_v1.c 为单线程串行服务的行为参考，不直接映射为多主共享内存。
- 先提供一张实际图像及其源帧号；96×54上下各补21行只是候选方案，桌面样图已出现分类翻转，A/C需确认最终96×96预处理。FNV覆盖提交的完整9216字节。
- 后续共同确认唯一DDR、AXI端口、地址转换、CPU缓存维护及实际SOF时间源；C 不单方面猜物理基址。

给 B：
- 读取 c3_hal/c3_hal.h；时间/I2C/GPIO 的调用格式和错误码已固定。
- tests/test_interfaces.c 包含可运行的 mock 后端，但不是传感器实测数据。
- 可以先按 API 开发器件级CRC/换算/校准逻辑；真实I2C/GPIO后端待板型/器件/引脚核对后绑定。
- 现有SoC并未启用I2C/GPIO，调用返回ENOTSUP；不能通过添加驱动头文件就宣称硬件已接入。
- 提供真实传感器型号、I2C速率要求、SCL/SDA电压/引脚、蜂鸣器有源/无源及极性后再实现后端。

测试：
- tools/test_c_interfaces.cmd：本机 MSVC C11 编译并执行状态机/时间回绕/HAL错误路径测试；另运行 Python UART解析测试。
- 使用其他主机编译器时，编译 cooperation_v1.c、c3_hal.c、test_interfaces.c，包含上述两个头文件目录即可。
- C1 RISC-V 固件同时编译该ABI和CLINT时间后端，避免只在PC能编译。

未完成：
真实DDR映射、A的视频/缩略图物理接入、板上缓存/CDC验证、整机CPU程序链接运行、真实I2C/GPIO后端、三路实采、实时AI及整机验证。此 v1 是 C 发布的图像软件ABI，尚待 A/B 评审；没有代替队友确认，也没有向队友发送消息。

