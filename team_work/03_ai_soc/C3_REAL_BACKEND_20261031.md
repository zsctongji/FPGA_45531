# C3 I²C/GPIO、公共时间和热图发布策略

2026-10-31。本阶段实现真实APB寄存器外设及RV32 MMIO回调，接入独立native SoC；验证使用实际RTL、数字总线从设备模型、主机C测试、RV32编译和保存的B热图。没有操作串口/JTAG、加载板卡、写Flash或触发物理蜂鸣器。物理管脚未冻结，当前不是可直接下载的最终整机。

## 工程与接口

- 外设：`projects/06_soc_c2/rtl/c3_apb_peripheral.sv`。
- native生成：`tools/prepare_c2_vendor.py`。原C2页继续使用`0x0000`；新增C3页`0x1000..0x10ff`，软件地址为厂家APB0基址`0xf8100000 + 0x1000`。只对native工程生效，不能用于旧C1/独立B诊断镜像。
- 软件：`c3_hal/c3_peripheral.[ch]`、`c3_sapphire_peripheral.[ch]`、`c3_thermal_publish.[ch]`。
- 公共时间：直接从同一个`c2_shared_time`实例导出的APB毫秒计数器，视频仍接原快照CDC。没有新增独立CLINT或传感器时钟纪元。
- C HAL升级为`C3_HAL_INTERFACE_REV=2`，追加`checked_now_ms`，`c3_now_ms`优先检查其返回状态，失败不改结果。**所有HAL调用者须用新头文件重新编译并整体零初始化结构体**；不要混用旧二进制结构体。现有`coop_*`序列化ABI v1、C2 APB v2.2不变。

原CLINT绑定仅保留给独立诊断。新外设绑定填充checked时间而不填充legacy `now_ms`；C3能力位为TIME|I2C|GPIO|CHECKED_TIME=15。能力表示接口存在，健康状态仍以每次返回值为准。

## C3页寄存器（页内字节偏移）

| 偏移 | 读写与含义 |
|---|---|
| 00 / 04 | RO ID=`0x43335031`，version=`0x00010000` |
| 08 | 状态：bit0 BUSY，1 DONE，2 NACK，3超时，4仲裁丢失，5总线卡住，6 SCL输入，7 SDA输入，8 IO/时间已使能；空闲时写1清完成/错误 |
| 0C | 命令：9 START+WRITE（含地址字节），8 WRITE，4 READ+ACK，20 READ+NACK，2 STOP，32恢复9脉冲后STOP，64中止释放并撤销GPIO使能 |
| 10 / 14 | TX / RX，低8位，非移位寄存器 |
| 18 | SCL分频，`ceil(100MHz/(5*bus_hz))`；3tick低、2tick高，默认400kHz；软件允许10k..1MHz，最终速率需与器件及实物匹配 |
| 1C | 单命令超时（APB周期），默认20ms，最大100ms |
| 20 | GPIO逻辑状态：bit0报警LED，bit1蜂鸣器 |
| 24 | ARM，写`0x43474131`启用，写0停用，复位默认停用；读回0/1 |
| 28 | 仅在停用时配置的有效低掩码；配置后未启用输出处于对应inactive电平，复位默认物理低 |
| 2C | 蜂鸣器连续开启上限，1..60000ms，默认5000ms；重复写ON不续期，超时全部停用 |
| 30 / 34 | IO/时间可用标志 / 配置的APB频率100MHz |

命令额外支持带STOP的字节形式10/6/22；当前C驱动统一使用独立STOP。不能在其他主机占总线时盲目恢复；本实现用于单主机传感器总线，仲裁丢失只负责释放，不宣称完整多主机调度。

I²C输入先双触发器同步，再做超过50ns的稳定采样滤波。分频相位、START/STOP及总线空闲保持按[NXP UM10204 Rev.7](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)的Standard/Fast/Fm+时序表设计；100k、400k、1MHz均通过理想PAD数字时序检查。该设计/仿真不能证明实际上拉、电容、上升/下降沿或电气一致性。

## 原生PAD连接与验证前提

native导出`c3_sensor_scl_read`、`c3_sensor_sda_read`及对应`*_drive_low`。Efinity双向GPIO的输出DATA必须恒0，OE接`drive_low`，输入接**实际PAD读回**。不能把输入接成`!drive_low`，否则看不到拉伸/仲裁。外层通用RTL等价关系为`assign pad = drive_low ? 1'b0 : 1'bz`，仅PAD边界可使用三态。

候选SCL=B3/J28.37、SDA=C3/J28.39、蜂鸣器=B5/J28.38，LED未指定。`integration/c3_pad_contract.json`仅为未应用的约束交接模板。须核对最终工程的LCD冲突、IO电压/上拉、PAD OE极性、蜂鸣器有效极性和冷启动表现；完成后才能置顶层`c3_io_enable=1`并传入软件`pins_verified=1`。A13保留传感器脚为输入，不等于已经接好此双向控制器。没有偷偷把候选引脚写成已通过的P&R约束。

`c3_io_enable`只允许与共同复位配合配置。默认复位输出低、I²C OE释放、GPIO未启用；有效低模块的冷启动静音不能据此承诺，极性核对前保持蜂鸣器断开。默认C24继续关闭live/MMIO，不会因构建本后端而访问传感器。

`c3_io_enable`是外层输入，未连接不代表逻辑0；板级封装在验证前必须明确绑0，验证后才可按复位配置切换。参考JSON中的禁止使能要求不是已经应用的物理约束。

## 软件接法

```c
static c3_peripheral_t peripheral;
static c3_hal_t sensors = {0};
static c3_sapphire_io_t mmio;
static uint8_t scratch[1664]; /* >=本次最大读取长度，最多4096 */
c3_peripheral_config_t cfg = {400000,20,200000,3000,0,0};
/* 仅在物理APB/IO/极性验收后设置这两个 verified 参数；默认0会拒绝绑定。 */
cfg.pins_verified = pins_actually_verified;
int rc = c3_sapphire_peripheral_bind(&peripheral,&sensors,&mmio,
                                    &cfg,scratch,sizeof(scratch),mapping_actually_verified);
/* rc==COOP_OK后，将 &sensors 提供给重新编译的B驱动。 */
```

绑定发生在共同复位后的初始化阶段，不支持热切换MMIO映射或替换正在使用的context。context、scratch和HAL必须活过服务；scratch必须与事务TX/RX分开，HAL、寄存器服务和B任务由同一调用者串行调度。

组合传输采用7位地址→START写地址→TX→重复START读地址→RX→最后NACK→STOP。最多4096B TX，RX受scratch容量约束。RX暂存在scratch，整笔成功且总线读回释放才复制到调用者；失败不把半帧交给B。总期限来自公共时间，同时有单命令硬件超时与有限轮询预算。NACK自动STOP；超时/仲裁/IO/时钟错误中止、停用输出并使服务poison，显式`c3_peripheral_recover()`检查公共时间、产生9脉冲/STOP且读回总线释放后才能继续。不重放失败事务。外部将SCL/SDA持续拉低时只能释放本FPGA的OE，不能保证线路物理变高。

底层MMIO提供有序volatile读写与RV32 `fence iorw,iorw`，没有虚构原SoC不存在的GPIO/I²C地址；新增地址由本轮RTL实际解码提供。它不捕获CPU总线异常，不应对旧镜像或未经验证的映射强行传入verified。调试中不得停住总线事务或单独停任一时钟域；共同复位负责清除所有权。

## 坏点发布策略

`c3_publish_thermal()`要求checked时间，校验当前ABI、完整转换标志、错误位、掩码和500ms年龄；未来时间拒绝。成功时原样复制输入并另给`valid_pixels / quality / age_ms`，失败不改输出或质量结果。

- `C3_THERMAL_STRICT`：768点全有效、flags=7、errors=0，返回FULL。
- `C3_THERMAL_ALLOW_BAD_620`：只接受唯一620号无效、767点有效、该槽为占位0、flags=3、errors=PIXEL_QUALITY(64)，返回MASKED。其他坏点、额外错误、虚假的全质量标志全部拒绝。

不插值、不把占位0当测温、不把3/64升级成7/0。下游须按位图计算并保留MASKED质量状态。B原`b_thermal_get`严格行为保留；对B组帧器的完成快照调用新发布接口，不能把任意`COOP_EIO`当有效热图。只有新接口明确返回OK后才可进入融合/历史。不同传感器若坏点不同需另行审核策略，不能沿用620白名单。

真实100条B记录已用当前C新接口回放：MASKED接受100条，严格拒绝100条，原始结构体/位图不变；旧B4候选策略也一并对照。该结果是历史数据验证，不是本轮实时采集或同步融合。

## 产物与验收

- `22_test_c3_backend.cmd`：实际外设RTL、100k/400k/1MHz数字时序、主机C测试、RV32对象及真实100条热图；报告`logs/c3_backend_check.json`。
- `tools/run_c2_selftest.py`：原49次加C3外设，共50次；保留完整1080p/视频/AI/CPU/TinyML并发检查。
- `tools/package_c3_backend.py`：将已校验RV32对象打包为`firmware/c3_peripheral_backend/libc3_peripheral_rv32.a`，供后续应用链接；不是FPGA配置或可独立执行固件。
- `15_synth_c2_native.cmd`：重新map含C3的native，保持唯一DDR。最新结果和源码/产物哈希见对应logs。
- C HAL变更后C24已重新构建，默认仍关闭实时MMIO。旧版本/旧697项数字是历史记录，最终包身份结果以重新运行`tools/verify_c24_package.py`为准。没有重新声称C1或A/B独立镜像包含新外设。

本轮最终结果：50次完整RTL回归PASS；C3专项包含外设故障/50ns毛刺、实际C2/C3同计数器APB联合仿真及3种速率数字时序，均PASS；主机后端49项检查及8个RV32对象PASS；100条历史热图的新C掩码发布PASS。native map为53,027 LUT4、53,539 FF、51 DSP48、6,715 ADD；仍未做P&R/电气验收。C24版本`c24-ddfd364d754dce06`，756项包身份检查PASS，live/MMIO默认关闭。RV32可链接库为19,778字节。旧HAL的接口参考16,036项及C4/replay 1,235,652项检查也通过。

C1仍保留原`c1-02a568e5375cc27b`的ELF/BIN/FPGA产物，没有因C3升级重标其源码。原C1构建目录内的3个旧HAL源码逐字节匹配原输入哈希，已冻结于`firmware/c1_static_person_detect/frozen_c3_hal/`；`C1_FROZEN_SOURCES.json`记录对应关系。C1验证器只允许这3个带原哈希的发布快照替代已演进的主源码，并继续对原生成overlay和二进制核对，527项PASS。新C3 API与C1旧接口不混用。

编译工具在本机偶尔首次启动`cc1/cc1plus/collect2`子进程失败。构建器仅对明确的Windows CreateProcess启动错误原命令重试一次，并保存原始诊断；实际语法、类型或链接错误不重试，未屏蔽任何编译告警。

尚需最终PAD约束、CDC/时序/P&R、板端SHT/MLX真实读数、完整MLX EEPROM/原厂换算路径、GPIO极性及冷启动、电气波形和真实同会话500ms验收。本阶段提供后端与发布接口，不替代完整传感器采集/换算任务或整机融合调度。
