# C24 CPU 固件交接

配套版本：`c24-d1fc40db3541b41f`。控制接口为 APB v2.2（`0x00020002`），图像描述符 ABI 为 v1。

- `tinyml_c24.elf/bin/hex/map` 为 RISC-V CPU 程序及调试信息，**不是 FPGA 配置文件**。
- 默认仅运行合成图案自检，之后输出 `LIVE_DISABLED`；三个现场构建开关均为0，不访问 C2 共享区/MMIO。
- 固件已链接，未上板执行；旧 C1 FPGA 配置不包含本版 C2/公共时间硬件，不能用于本版现场取帧。
- 构建入口为仓库根目录 `16_build_c24.cmd`；主源码在 `team_work/03_ai_soc/c24`，生成的 `tinyml_c24` SDK工作副本不重复上传，准备脚本会从已有厂家应用创建它。
- 文件字节数与 SHA256 见 `logs/firmware_c24.json`；模型、输入和源码身份见 `C24_INPUT_MANIFEST.json`。
- 原机器上的42次RTL回归、38个日志测试及666项配套检查为离线证据。历史报告含该机器的绝对路径；其他电脑需安装工具并按说明重建，不代表下载仓库即可直接验证原机器的综合输出。

统一时间、串口采集与验收步骤见 [TIME_AND_C24_ACCEPTANCE.md](../../team_work/03_ai_soc/TIME_AND_C24_ACCEPTANCE.md)。烧录前仍需核实板型、Flash布局、实际APB/DDR地址和配套FPGA文件。
