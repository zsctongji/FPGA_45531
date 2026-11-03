# LED 最小上板工程

工作工程 `D:\FPGA_2026_T3_P3\projects\01_led\LED_8bit_Test.xml` 已通过 Efinity 的综合、Interface Designer、布局布线及配置文件生成。入口为 `03_compile_led.cmd`。本次同时检查 LPF/HEX 为新生成文件，并拒绝负裕量告警；证据为 logs/efinity_led_compile.json。尚未下载到实体板。

厂家原例程在两个时钟之间切换按键消抖，再把使能接入 54 MHz 的 LED 控制，产生真实跨时钟路径。工作副本已把该按键与 LED 固定到同一时钟，并为各域加入复位同步释放。按键输入先双寄存器同步，再做稳定时间消抖，15 ms 计数单位已修正；释放后只产生一个脉冲。8 个 LED 现在都有驱动。

消抖功能通过短按、抖动、保持释放、中途复位和两次完整按下/释放检查；可用 `08_test_led_key.cmd` 重复。该检查加速了计数参数，不证明实体按键与 LED 已运行。

`constraints/led_clocks.sdc` 采用本次 Interface Designer 生成的四个 fabric 时钟，保留原相位/周期，不使用未填写的 HSIO 占位值。未用 false path 掩盖原来的时钟切换路径。外部管脚/电压配置未修改；沿用厂商 C4 时序模型，仍须与用户实际芯片/PCB 版本核验。

按键 0 同时连接厂家 PLL reset，作用包含复位；其余键可切换对应 LED 分组的闪烁计数位。编译成功后，必须先核对实物和下载接口，才能用匹配的板卡程序进入物理验证。
