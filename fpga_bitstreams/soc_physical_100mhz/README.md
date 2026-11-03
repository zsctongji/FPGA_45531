# C7 100 MHz 实板验证镜像

soc_physical.bit 用于 JTAG 临时配置 FPGA SRAM。它已在本次 Ti60F225 上完成 CPU DDR/缓存基础测试和原 C1 六张静态图推理，原始 INT8 分数与桌面参考完全相同。

CPU 程序须另用经完整读回校验的 JTAG 调试加载；FPGA .bit 不包含本次 C1 应用。入口 tools/run_c7_board_acceptance.py，详见 team_work/03_ai_soc/C7_BOARD_ACCEPTANCE_20261101.md。当前 SDK/固件仍使用 100 MHz CLINT/APB，CPU/core 为 100 MHz。

.hex 是配置归档文件，本包没有生成 FPGA+CPU 的 Flash 合并镜像。请使用默认释放的 KEY3，保持实时映射关闭。尚未验收外部 DMA stale-cache 负例、真实视频/传感器并发及 C7 冷上电/Flash 自动启动；physical_release_ready=false。

本包不是旧 tinyml_225mhz 独立工程；构建、镜像和板上证据的 SHA256 见 BUILD_RECORD.json。
