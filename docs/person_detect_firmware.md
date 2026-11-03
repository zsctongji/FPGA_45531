# 人体检测固件：已构建，待板上执行

2026-10-18 实际使用 xPack RISC-V GCC 13.4.0 与 GNU Make 4.4.1 构建成功。源工程为厂家 `projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone/tinyml_pdti8`。入口 `07_build_person_detect.cmd` 强制重新编译，避免继承厂家 build 中的历史文件；本次结果来自 build_ours，日志在 logs/firmware_person_detect.json。

它运行 MobileNet 人体分类模型，输入为 96×96 灰度图片，输出“有人/无人”两个分数；不输出目标框。当前 main.cc 使用厂家提供的静态有/无人图片，串口 DebugLog 调用 BSP 的 UART 函数。尚未接入实时摄像头、温度或环境数据，未执行实际板上推理。

| 生成文件 | 大小 | 用途 |
|---|---:|---|
| tinyml_pdti8.elf | 12,022,336 字节 | 含调试信息的 ELF32 RISC-V 程序，入口 0x1000 |
| tinyml_pdti8.bin | 1,417,720 字节 | CPU 原始指令/数据镜像 |
| tinyml_pdti8.hex | 3,987,766 字节 | CPU 程序的 Intel HEX 表示 |
| tinyml_pdti8.map | 1,145,018 字节 | 链接布局与符号，定位内存使用 |

整理副本在 `D:\FPGA_2026_T3_P3\firmware\static_person_detect`。**CPU HEX 不能作为 Ti60 FPGA 配置比特流直接烧录。** 配套 TinyML FPGA 工程已完整编译通过，CPU/加速器为实际 225 MHz，内存和 CLINT 为 100 MHz。仍需核对实体板和 Flash，按对应布局集成 CPU 程序，并实测启动/推理。

## 引导 ROM 与配套布局

厂家默认加载容量约 124 KiB，小于本次 1.4 MB 应用。已从同一 BSP 实际构建新引导程序，二进制 664 字节，ELF 入口 0xF9000000，使用厂家 C 启动和 SPI 驱动；C 引导程序无 C++ 构造函数，编译时关闭无用的 libc 初始化。四个 8-bit ROM lane 各 1024 行，组成 4096 字节 ROM，已嵌入这次重新编译的 FPGA 配置。

加载布局：Flash 0x00380000，RAM 0x00001000，加载容量 0x00400000（4 MiB）。反汇编确认复制终点 RAM 0x00401000。外围/CLINT 时钟没有随 i_sysclk 的降频变化，BSP 计时基准保持 100 MHz。物理 Flash 必须容纳该范围；实际板型/容量与写入方法待实物核验。当前仅交付独立 FPGA/CPU 文件，没有生成或写入完整 Flash 合并镜像。

来源和哈希见 logs/bootloader_build.json，原始 ROM 保存在 projects/03_tinyml/original_bootrom，厂家资料未改动。改动 ROM 后需要重新编译 FPGA，已完成。可用 tools/build_tinyml_bootloader.ps1 重建，但重建之后也必须重新运行 05_compile_tinyml.cmd。

## 修复及可复现记录

- 从同一厂家包的 tinyml_ypd 恢复 pdti8 缺失的 FlatBuffers 和整数内核头文件；先核对两者的 TensorFlow schema_generated.h 哈希一致。
- C++ 编译剔除旧的 -ffreestanding，保留 C 的裸机编译、-fno-builtin、nosys、厂家 startup 和 linker。
- main 改为标准 int main(void)，结束返回 0；厂家启动代码返回后仍进入 mainDone 循环。
- 链接 GCC 同一 RV32/ilp32 的 crtbegin.o、crtend.o，为 C++ 构造函数提供运行时元数据。
- ISA 使用 rv32im_zicsr_zifencei、ABI ilp32，匹配此 BSP 的整数核配置。原模型和静态测试图片未改动；准备记录在源工程的 PREPARATION_RECORD.json。

链接报告 RAM 使用 3,686,880 字节，包含厂家默认预留栈，region 大小为厂家 linker 的 128 MiB；这不是实际 DDR 实测值。Newlib nosys 给出未实现的文件/进程系统调用告警；当前串口日志使用 BSP UART。须在目标 SoC 验证启动、UART、TinyML 自定义指令、输入/输出、真实延迟和内存，不把链接成功当作准确率或硬件推理成功。

工具来自项目官方发行库，发行 SHA-256 和 ZIP 成员 CRC 已核验，许可文件随工具保留。出处：[xPack RISC-V GCC 13.4.0](https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/releases/tag/v13.4.0-1)、[Windows Build Tools](https://github.com/xpack-dev-tools/windows-build-tools-xpack/releases/tag/v4.4.1-3)。Efinix 将 xPack GCC 列为其 RISC-V IDE 的组件，见[原厂软件说明](https://www.efinixinc.com/docs-html/riscv-embedded-ide-ug/topics/riscv-embedded-software-ide-installation.html)；本项目使用独立命令行工具，不声称已经安装完整 IDE/OpenOCD 调试器。
