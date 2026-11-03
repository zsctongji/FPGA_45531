本目录整理本次由 Efinity 实际生成的独立 FPGA 配置文件。
led：LED 最小调试工程。
camera_preprocess：厂家 MIPI/DDR/HDMI 链路加入灰度预处理。
tinyml_225mhz：225 MHz CPU/加速器 SoC，内置新的 4 MiB 引导 ROM。
camera_color：彩色摄像头直通对照工程（完成编译后归档）。
camera_motion：灰度摄像头 + 96×54 帧差运动红框；2026-10-19 完整编译和最终时序检查通过。

它们是分阶段上板工程，尚未在用户实物上运行，也不是三模态整机比赛程序。
使用前须核对实际 PCB、芯片和接口与对应原理图一致。
这里的 FPGA HEX 与 firmware/static_person_detect 的 CPU HEX 用途不同。
TinyML 的 CPU BIN 另需按 Flash 0x380000 和配套 bootloader 布局处理，尚未生成完整 Flash 合并镜像。
