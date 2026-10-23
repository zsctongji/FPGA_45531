# 群资料获取与板卡核对

来源为用户展示的“2026嵌入式竞赛易灵思赛道技术群”群文件，不依据群公告发送邮件、注册账户或发消息。

## 已取得

- V4 DEMO 板软硬件说明：`references/Ti60F225_V4_board_manual.pdf`，110 页，9,756,637 字节，2026-10-17 从用户已登录的 QQ 群文件下载。
- SHA-256：426A577CC3A544546F2BF1AD60A1F233541B7D6361764794E48B11ADA0C2E4F2。
- 手册第 7 页有板卡布局；第 12 页有时钟表；第 34 页有按键/LED；第 97 页有 CSI 到 HDMI 工程的版本关系。上述关键页已渲染目视检查。
- 当前手册描述的板卡有 HDMI RX/TX、千兆网、16 位 DDR3、MIPI、FT4232HL 下载/串口；仅据下载到手册不能证明用户实物就是此板版本。

## 软件与 IP 版本关系

手册第 97 页：CSI/HDMI v4 使用 Efinity 2025.2.288.4.15；v5/v7 使用 2026.1.132.2.19。部分 CSI RX IP 存在版本适配问题，需优先使用原工程附带的配置并检查日志；软件可下载不表示所有 IP 已更新兼容。

用户提供的 `efinity-2026.1.132-windows-x64.tar.gz` 已校验并解压到 D 盘 tools/efinity/2026.1。2026-10-18 已通过普通 Windows .cmd 入口验证完整编译、Interface Designer 和配置文件生成。初期 QtGui 直接导入错误保留为历史诊断，不需重复下载相同包。原公告网盘入口曾被浏览器策略拦截，本次未绕过。

## 已完成下载与解压

Ti60F225 DemoBoard V4 完整包：1,134,244,849 字节，SHA-256 fe1998757c1655a4ea8cf109b637c3bd1674d75ca7caad0175b984a5e7b8b85f。ZIP 全部成员 CRC 已检查，解压到 vendor_projects/Ti60_V4，包括原理图、DDR3、MIPI、HDMI、网络、LED、UART、RISC-V 和驱动资料。

TinyML Demo：315,034,278 字节，SHA-256 c0826993141736daaec086ee1aae0a8458875ec09703439b327368a5095efc7a，ZIP 全成员 CRC 已检查，解压到 vendor_projects/TinyML。摄像头 v7 嵌套 RAR 也已单独解压。两个独立工程均已由本次 Efinity 实际完成综合；原厂历史 outflow 不作为本次证据。

Efinity 包：1,106,750,295 字节，SHA-256 0289e5c33a8b1b4787cdce31acde63073c051bdcb83d5f0264e833d2a6ed75b2。各解压目录中的 EXTRACTION_RECORD.json 保存来源及核对记录。大型原始包统一在 D 盘 vendor_archives，未执行包内驱动安装器。

## 下一步待确认

用户板卡完整型号/版本、摄像头模组、红外与温湿度传感器、屏幕和实际连接。手册的管脚与电压须与对应工程配置以及用户实物一致，当前没有把手册候选管脚写成可直接烧录的约束。
