onerror {resume}
quietly WaveActivateNextPane {} 0
add wave -noupdate /led_ctrl_tb/led_ctrl_inst/clk
add wave -noupdate /led_ctrl_tb/led_ctrl_inst/rst_n
add wave -noupdate /led_ctrl_tb/led_ctrl_inst/en
add wave -noupdate -expand /led_ctrl_tb/led_ctrl_inst/led
add wave -noupdate -radix unsigned /led_ctrl_tb/led_ctrl_inst/cnt
add wave -noupdate -expand /led_ctrl_tb/led_ctrl_inst/en_r
add wave -noupdate /led_ctrl_tb/led_ctrl_inst/cnt_end
TreeUpdate [SetDefaultTree]
WaveRestoreCursors {{Cursor 1} {0 ps} 0}
quietly wave cursor active 0
configure wave -namecolwidth 150
configure wave -valuecolwidth 100
configure wave -justifyvalue left
configure wave -signalnamewidth 1
configure wave -snapdistance 10
configure wave -datasetprefix 0
configure wave -rowmargin 4
configure wave -childrowmargin 2
configure wave -gridoffset 0
configure wave -gridperiod 1
configure wave -griddelta 40
configure wave -timeline 1
configure wave -timelineunits us
update
WaveRestoreZoom {390014 ps} {390810 ps}
