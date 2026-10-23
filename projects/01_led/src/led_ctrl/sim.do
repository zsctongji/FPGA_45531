set TB_NAME 	led_ctrl_tb
set SWITCH	RTL

#Define vlib
vlib work

#Compile files in sim folder(verilog)

#Compile user files
vlog +define+$SWITCH ./\*.*v

#Load the design.
vsim -t ps +notimingchecks -gui -voptargs="+acc" work.$TB_NAME
	
onerror {resume}

#Log all the objects in design. These will appear in .wlf file
log -r /\*
do wave.do

#Change radix
radix hex

#Run simulation
run 20ms

#Zoom the wave
wave zoom full 
