# C4 电脑端输入桥、桌面参考与 C3 回放

2026-10-24。无板卡条件下完成。C1固件和原厂模型保留；本轮没有下载或网络上传。

## 一键重现

根目录双击 12_test_c4_pc.cmd；终端也可运行 tools/run_c4_pc_checks.ps1。
需要已安装的本机 MSVC C11 工具、Python3.11、项目内RISC-V GCC。脚本在 build/pc_ai_packages 安装/使用锁定的 LiteRT 2.3.0 及依赖，不安装到系统包目录。安装来源与用法参考 [Google LiteRT 官方指南](https://developers.google.com/edge/litert/overview)；本项目保留 Interpreter 的CPU参考模式以对照现有TFLite Micro模型，并不迁移板上运行时。

依次执行：
1. Windows原生C4/传感器回放测试及DLL构建。
2. 六张原厂静态样图的实际PC推理，以及24次C输入桥→PC推理回放。
3. 日志比较器负例测试、原C1解析器回归。
4. C4桥、C3回放和TFLM适配器的RISC-V对象编译检查。
5. 原C1配套文件的527项一致性复核。

总状态为 logs/c4_pc_checks.json。PASS仅指其scope；board_inference_passed、live_camera_passed、preprocess_policy_approved均为false。虚拟传感器是预设字节/返回码/虚拟时间，不是实际采样或器件物理模型。

## 文件入口

| 文件/目录 | 用途 |
|---|---|
| c4/c4_bridge.{h,c} | 96×54补边、GRAY8→厂家INT8转换、取帧校验/过期/顺序检查、推理调用及释放 |
| c4/c4_tflm_adapter.{h,cc} | 供后续整机复用的MicroInterpreter回调；本轮只做RISC-V编译检查，未链接成新的实时固件 |
| c3_hal/c3_replay.{h,c} | I2C事务脚本、有限虚拟超时、NACK、逻辑GPIO状态；供B测试驱动 |
| tools/run_pc_ai.py | 实际桌面模型推理和C桥回放 |
| tools/pc_model_compat.py | 审计后的桌面元数据兼容转换 |
| logs/pc_ai/c1_reference.json | 六张样图的原始INT8分值、输入哈希、运行时版本及PC耗时 |
| logs/pc_ai/c4_replay.json | 24次链路对照、只读原图保持、槽释放和转换校验 |
| logs/pc_ai/preprocess_policy.json | 全图/补边/拉伸/中心裁剪分值对照 |
| logs/pc_ai/model_compatibility.json | 原模型/桌面兼容模型哈希及14个字段的修改位置 |
| tools/compare_c1_reference.py | 将今后真实C1串口日志与桌面参考逐样本比较 |

接收路径是串行所有权服务的可执行参考，不含物理AXI/DDR、cache维护、DMA或CDC。真实视频帧完整性仍需A/C实现并验证。
共享原图始终保持GRAY8；只有独立模型工作缓冲转换为int8。检查原图FNV后再转张量，并分别记录两者校验。校验错误、过期/未来时间、重复/倒序帧、模型失败均不产生有效推理结果；已取走槽在失败路径也释放。frame_id支持自然回绕，但有效顺序跨度必须小于2^31。

## 重要模型兼容性发现

未经修改的厂商模型不能被本轮LiteRT2.3.0加载：14个一维INT32卷积偏置张量的quantized_dimension为3。
代码只在 build/pc_ai/person_desktop_compat.tflite 生成桌面副本，将这14个明确列出的字段改为0：
tensor 33,36,40,44,48,52,56,60,64,68,72,76,80,84。
每个都已核对为CONV_2D/DEPTHWISE_CONV_2D的第三个输入。验证所有模型数据缓冲区逐字节相同，张量形状、类型、scale/zero_point不变；原模型和C1固件不改。

- 原模型SHA256：808cfdfc0cf3a6fa6f6fa26bfa379ea97c16d5db7334637766e39c3408502e9d。
- 桌面副本SHA256：77cac99d46416295fc3ec9cf752dec8e0c8aafd9421475da6c86439aee22e1c4。
- 桌面CPU参考使用BUILTIN_REF、单线程，原始分值见日志。它是兼容副本的结果，尚未实测与旧版TFLM/TinyML加速器的数值等价；不能称为未经修改原模型的桌面执行结果。
- 将来对照采用严格原始INT8比较，不自动放宽误差。若不一致，保留分层诊断证据，不能直接把差异归因于某一方。

将来拿到板上单次启动日志后：
~~~powershell
python .\tools\compare_c1_reference.py .\logs\c1\uart_实际时间.log
~~~
PASS是日志一致性比较，不独立证明真实板卡来源。比较器的单元测试使用合成日志，未生成冒充实测的UART记录。

## 已测得的输入策略风险

以下是“person原始INT8分值”，不是概率。输入来自同六张厂商样图；96×54通过最近邻纵向重采样构造，不是真实相机输出。crop为96×54中取中心54×54后缩放至96×96，stretch为纵向最近邻拉伸至96×96。

| 样图 | 原图 | 补边 | 拉伸 | 中心裁剪 |
|---|---:|---:|---:|---:|
| person | 113 | 17 | 105 | 104 |
| no_person | -57 | -6 | -69 | -30 |
| people1 | 93 | 56 | 69 | -69 |
| people2 | 57 | -65 | 108 | -6 |
| no_people1 | -51 | -43 | 21 | -12 |
| no_people2 | -111 | -81 | -105 | 14 |

原六张样图与原标签一致；补边使people2翻转，拉伸使no_people1翻转，裁剪使三张翻转。样本很少且输入变换不同，不能据此宣布某策略准确率高或直接替换摄像头方案。
A/C应优先获取带原始画面的实际图像对，评估人员位置/尺度/光照和静止场景，再固定取图策略。当前96×96软件接口不变，补边策略仍待验收。

## 导入 A 的录制图像

只接受无头RAW GRAY8：
~~~powershell
python .\tools\run_pc_ai.py --gray C:\实际路径\frame.gray --height 54
~~~
长度必须为96×54；脚本按当前候选补边。height=96时要求9216字节且直接使用。日志会标为user_recorded_GRAY8_unverified_source，帧号/时间是本地回放编号，不能当作真实摄像头采集证明。PGM/JPEG/PNG需先明确转换，不能把文件头送入模型。

## 仍需硬件完成

真实摄像头图像、同一DDR控制体系、CPU/DMA缓存一致性、CDC/时间源、传感器驱动和上板推理性能。C4对象编译通过不等于形成可烧录的实时整机。

