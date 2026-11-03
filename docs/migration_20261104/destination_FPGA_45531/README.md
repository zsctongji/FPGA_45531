# FPGA A/B/C 源码快照

2026-11-04 整理的团队源码压缩包，包含 A/B/C 协作源码、本机最新 C 侧 RTL/固件、接口说明、验证与构建脚本，以及当前摄像头预览工程的配套 IP 输入。

- 源码包：[FPGA_ABC_sources_20261104_003514.zip](FPGA_ABC_sources_20261104_003514.zip)，约 56.5 MiB，共 7042 个归档文件。
- 校验文件：[SHA256](FPGA_ABC_sources_20261104_003514.sha256.txt)。
- 校验结果：[verification.json](FPGA_ABC_sources_20261104_003514.verification.json)：ZIP CRC、逐文件 SHA256 及当前预览 XML 的 112 个设计文件输入核对通过。

下载压缩包时，请使用文件页面的 Download/Raw 按钮，或克隆本仓库后解压。先阅读包内 `PACKAGE_README.md`；目录、原始路径和逐文件摘要见 `PACKAGE_MANIFEST.json`。解压至独立目录，迁移后需调整原工程绝对路径，并另行安装 Efinity 2026.1.132、RISC-V GCC、Icarus 与 Python 依赖。

当前隔离预览已确认实时摄像头画面，记录达到 1920×1080；PHY 活动告警仍未解决，正式摄像头/真实 TinyML/完整并发与最终冷启动验收尚未完成。该快照不是最终验收发布版。

本包不含开发工具安装、Git 元数据、账号许可证、采集图片和最终 bitstream。包含的厂家 IP/SDK 沿用各原文件的授权，不因上传而改变授权范围。完整说明和诊断记录位于压缩包内。
