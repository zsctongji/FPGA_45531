# 摄像头显示预处理

工作工程：D 盘 `projects/04_camera_preprocess/ti60f225_oob.xml`，由 `projects/02_camera` 的厂家 v7 直通例程复制后修改。厂家资料原件保留在 vendor_projects。外围配置文件未改动，哈希记录在 PREPARATION_RECORD.json；实物管脚仍待核验。

`rtl/video_display_preprocess.v` 在厂家 gamma/颜色选择之后、DVI/TMDS 编码之前处理一拍一个 RGB888 像素。使用同一个 HDMI 像素时钟，将 RGB/HS/VS/DE 一起延迟两级；HS/VS 在消隐期继续传播，不以 DE 为门控。有效图像尺寸不裁剪。

| 顶层 DISPLAY_MODE | 显示 | 处理 |
|---|---|---|
| 0 | 原彩色 | RGB 两级寄存 |
| 1（默认） | 灰度 | (77R+150G+29B+128)>>8，再一级对齐 |
| 2 | 黑白 | 灰度不小于 DISPLAY_THRESHOLD（默认 128）时输出白，否则黑 |

三种模式均通过颜色主值、随机像素、消隐、HS/VS/DE 相位和中途复位检查。默认灰度副本已通过完整 Ti60 编译和最终 setup/hold 检查。保留厂家 gamma 分支的通道选择关系，不根据未实测画面猜测交换红蓝。工程已有显式 debug_edb_top；关闭了重复的 post-map 自动调试插入，原显式 RTL 保留。

工程仍使用厂家 1920×1080 参数；这只是例程参数，尚无真实采集/帧率证据。未把 Sobel 的 (W-2)×(H-2) 裁剪输出直接接入固定尺寸显示链路。该显示预处理不是人体检测，也未含热力图、环境文字或报警叠加。
