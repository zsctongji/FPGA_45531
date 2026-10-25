# GitHub 协作与本机工程

目标仓库：`zsctongji/FPGA_cooperation`。本目录中的说明是上传准备的一部分，实际提交/分支/上传结果以 `logs/github_upload_result.json` 为准。

## 仓库里有什么

- `rtl`、`sim`：自编图像/传感/融合模块及自动测试。
- `projects/01_led` 至 `06_a_units`：已有工作工程的源码、约束、IP、CPU SDK、模型和 ROM 初始化数据，保留原有版权声明。
- `firmware/a_side`：供统一 SoC 接入的 C 读取/分包接口。实际 CPU 应用源代码同时位于 `projects/03_tinyml/embedded_sw`。
- `tools`：构建/仿真脚本及 PC 接收工具，包含 `tools/a_side`。
- `docs`、`team_work`：上手说明、三人分工、接口、个人章节与待测记录。
- `logs`：所选既有测试状态，属于历史证据；复制到新电脑后应自行复现。

本次上传不捆绑 Efinity、Icarus、RISC-V GCC 等软件运行时，不上传原始厂家压缩包、重复源码交接大包、许可证密钥、账号凭据和编译中间缓存。项目需要的模型、ROM 初始化文件和源码版权声明保留；不能只下载几个 .v 文件便运行完整工程。

## 队友第一次使用

1. 下载/克隆完整分支，建议置于 `D:\FPGA_2026_T3_P3`；已有工程先放另一目录对比，避免覆盖自己的未提交修改。
2. 阅读 `docs/A_开始这里.md`、`team_work/shared/a_interface_v1.md` 和三人分工文档。
3. 分别安装原厂 Efinity 2026.1.132、Icarus 12、RISC-V GCC 13.4.0；脚本默认按本地 `tools` 中的约定目录寻找软件。软件资格/许可证由各自账户申请，不能上传共享许可证密钥。
4. PC 接收演示可通过根目录 `12_A_PC_demo.cmd` 启动；需要先将 Efinity Python 放到脚本约定位置，或使用本机 Python 3.11+ 直接运行 `tools/a_side/demo.py --output logs/a_side/pc_demo`。
5. 先跑基础测试，再接实际 PCB/相机/传感器。`SYNTHETIC` 图像和 `saved: 2` 仅代表 PC 演示数据，不表示摄像头或 AI 已上板。

## 后续协作

各人修改前先同步远端，分别在自己的分支提交，通过 Pull Request 汇总。推送前检查 `git status`，避免把安装软件、下载资料、临时缓存或凭据加入仓库。不要强制覆盖队友分支。

上传整理只同步源文件，不重新执行 FPGA 布局布线或修改硬件配置；历史编译状态与实物待测边界保持原样。
