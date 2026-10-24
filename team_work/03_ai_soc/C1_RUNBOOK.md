# C1 静态推理：电脑端准备与上板验收

2026-10-24。用户确认板卡暂时不在手边；本轮不打开串口、不下载、不改原厂引脚。C1 只有真实板上运行并保存证据后才能关闭。

## 工作位置与重建

- 原始基线：projects/03_tinyml/.../standalone/tinyml_pdti8，保留不改。
- C1 主源码：team_work/03_ai_soc/c1/main.cc。
- C2 ABI：team_work/shared/include/cooperation_v1.h。
- C3：team_work/03_ai_soc/c3_hal/。
- tools/prepare_c1.py 将基线复制为同级 tinyml_c1，并覆盖 C1/C2/C3 文件；该 app 是构建工作副本，后续改上述主源码，避免直接改副本又被准备脚本覆盖。
- 根目录 11_build_c1.cmd，或 PowerShell 执行 .\tools\build_c1.ps1 -Jobs 4。
- 依赖 Python 3、项目内 xPack GCC 13.4.0、Windows Build Tools 4.4.1。本轮编译脚本显式设置进程内工具子目录，Python 负责创建对象目录；不修改系统 PATH。
- 产物：firmware/c1_static_person_detect/tinyml_c1.{elf,bin,hex,map}；输入/版本清单 C1_INPUT_MANIFEST.json。
- 记录：logs/firmware_c1.json、firmware_c1.log、firmware_c1_elf.txt。

固件增加早期 bsp_init、256-word 程序自有 RAM 区四种图案读写、模型和张量类型/形状检查、六次 Invoke 及样本身份/时间日志。RAM 探测可能通过缓存，只验证当前程序的基础内存读写，不能称为完整 DDR 物理测试。
本轮的诊断发布使用 -g0，保留 ELF 符号和 map，省去体积较大的 DWARF；不改变模型或加速器配置。logs/firmware_c1.json 记录编译范围和实际产物哈希。
原始模型已通过本机 FlatBuffers 结构检查：input scale_bits=0x3c008081、zero=-1；output scale_bits=0x3b800000、zero=-128。这不是模型执行结果。模型量化元数据与灰度像素到张量的预处理是两个不同边界，当前保留厂家原例程的转换，后续须对比 golden。
推理失败立即输出 FAIL，不读失败调用残留的输出。输出两个原始 int8 分值、输入/输出 scale 的 IEEE754 位表示和 zero point。分数不是人体框或经过校准的概率。

## 到板前准备

1. B 确认 PCB 版本、芯片、电源、Flash 型号/容量、FTDI 通道及 UART；保留照片和接线版本。当前电脑的 COM3/4/5/6/8/11 为蓝牙端口，不能据此选择板卡串口。
2. 配套 FPGA 为 fpga_bitstreams/tinyml_225mhz 中已归档配置；其 225 MHz CPU/加速器、100 MHz CLINT/外围和 4 MiB 引导 ROM 与 C1 BSP 一致。不要改动现有加速器配置。
3. FPGA 配置和 CPU 固件是不同文件。CPU ELF 用于经核实的调试加载；CPU BIN 可按核实的 Flash 布局写入；CPU Intel HEX 的地址起于 RAM 0x1000，不能直接当 FPGA 配置烧录。
4. 现有 bootloader 从 Flash 0x00380000 复制 0x00400000 字节到 RAM 0x1000，因此 Flash 地址至少要覆盖 [0x380000,0x780000)。仅程序不足 4 MiB 不等于物理 Flash 符合此范围。
5. 写入前由对应下载工具文档/板型验证 FPGA 配置区与应用区无重叠、地址单位正确、布局适用。当前不提供未经核实的合并镜像或自动擦写脚本。FPGA、CPU 文件和输入清单一起保存 SHA256。

## 上板日志

先准备好经过核实的 FPGA/CPU 加载方案，再运行：
~~~powershell
.\tools\capture_c1_uart.ps1 -Port COM实际端口 -Seconds 120 -BoardPortConfirmed
~~~
脚本设置 115200 8N1，不拉 DTR/RTS、不发送串口命令；捕获开始后手动启动/复位板卡。一个日志只记录一次完整启动。若推理超过捕获时间可增加 Seconds（上限600）。
~~~powershell
python .\tools\check_c1_uart.py .\logs\c1\uart_实际时间.log --output .\logs\c1\validation.json
~~~

正常顺序：BOOT → HAL → RAM_PROBE → MODEL → OUTPUT → 六组 BEGIN/RESULT/TIME → DONE。
- BOOT/DONE 版本与输入清单一致；
- 模型和每张张量 FNV 与清单一致；
- 六次 Invoke 成功，person/no_person 原始分值及预期标签记录完整；
- CLINT ticks 与起止毫秒基本一致，打印/校验也会增加少量时间；
- 记录来源为 static，frame_id=0..5 是静态样本编号，不是真实摄像头帧号；
- checker 要求六张均符合样本预期才 PASS。若不同，应保留失败记录检查，禁止改标签/阈值掩盖问题。

checker 只检查日志一致性；合成日志也可满足格式，因此通过不单独证明板上运行。必须另附板卡/下载版本和实际采集证据。六张样图结果不能声称泛化准确率。
还需在有可用的电脑端同模型推理环境时建立 golden 输出，比较板上原始分值；本轮未安装 TensorFlow、未生成真实 golden 输出。

## C1 完成条件

配套文件已核对 → 实物启动 → 六次推理和校验记录 → 真实时间测量 → 与基准输出对比 → 重新上电复现。卡在 Invoke 时若无 RESULT/DONE，验收工具必须报失败；后续可增加硬件 watchdog。本轮未实现推理超时抢占。

