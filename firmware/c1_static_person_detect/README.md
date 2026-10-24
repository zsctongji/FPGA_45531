# C1 诊断固件

CPU 文件，不是 FPGA 配置文件。输入为六张原厂静态样图；没有实时摄像头或真实传感器输入。

主说明：team_work/03_ai_soc/C1_RUNBOOK.md。
构建：根目录 11_build_c1.cmd / tools/build_c1.ps1。
源码：team_work/03_ai_soc/c1/main.cc；tinyml_c1 是生成的工作副本。
版本及输入校验：C1_INPUT_MANIFEST.json。
本地配套文件校验：从工程根目录运行 python tools/verify_c1_package.py，生成 C1_PACKAGE.json。

ELF32 RV32IM，RAM 入口 0x1000。配套 FPGA 位于 fpga_bitstreams/tinyml_225mhz。
现有引导布局为 Flash 0x380000 → RAM 0x1000，复制 4 MiB；具体 Flash 容量/配置区/下载方式需实物确认。
严禁把 CPU HEX 当 FPGA HEX；本包没有完整 Flash 合并镜像。

板卡暂时不在手边，board_inference_passed=false。编译、结构检查和主机测试均不能替代真实板上推理。
