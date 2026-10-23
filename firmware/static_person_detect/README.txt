这是实际交叉编译得到的 RISC-V CPU 静态图片人体检测例程。
它不是 FPGA 完整配置比特流；请勿直接作为 Ti60 配置文件烧录。
ELF32 RISC-V，入口 0x1000，须与项目 03_tinyml 的 SoC/BSP/bootloader 配套。
软件构建已通过，真实板上启动/推理尚未执行，实时摄像头与三模态融合未集成。
完整说明见 docs/person_detect_firmware.md，构建记录见 logs/firmware_person_detect.json。
