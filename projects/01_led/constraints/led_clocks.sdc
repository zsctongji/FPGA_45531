# Fabric clocks copied from fresh Interface Designer output; asynchronous buttons are synchronized in RTL.
create_clock -period 12.500 -name osc_clk [get_ports {osc_clk}]
create_clock -waveform {10.000 20.000} -period 20.000 -name clk_50m [get_ports {clk_50m}]
create_clock -period 40.000 -name clk_25m_x2 [get_ports {clk_25m_x2}]
create_clock -waveform {9.260 18.519} -period 18.519 -name clk_54m [get_ports {clk_54m}]
