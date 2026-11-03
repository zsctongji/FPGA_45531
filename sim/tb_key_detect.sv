`timescale 1ns / 1ps
module tb_key_detect;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, key=1;
    wire pulse;
    integer pulses=0;
    key_detect #(.CLK_FREQUENCY_MHz(1),.DEBOUNCE_MS(1)) dut(.clk(clk),.rst_n(rst_n),.i_key(key),.key_sw_en(pulse));
    always @(posedge clk) begin
        #1;
        if(pulse) pulses=pulses+1;
    end
    task cycles(input integer n);
        repeat(n) @(negedge clk);
    endtask
    initial begin
        cycles(3); rst_n=1;
        cycles(1100); if(pulses!=0) $fatal(1,"idle pulse");
        key=0; cycles(1100); if(pulses!=0) $fatal(1,"press pulse");
        repeat(6) begin key=1; cycles(20); key=0; cycles(20); end
        if(pulses!=0) $fatal(1,"bounce pulse");
        key=1; cycles(1100); if(pulses!=1) $fatal(1,"release must pulse once");
        cycles(2000); if(pulses!=1) $fatal(1,"held release must not repeat");
        key=0; cycles(700); key=1; cycles(1100); if(pulses!=1) $fatal(1,"short press must reject");
        key=0; cycles(300); rst_n=0; key=1; cycles(3); rst_n=1;
        cycles(1100); if(pulses!=1) $fatal(1,"reset must flush partial press");
        key=0; cycles(2100); key=1; cycles(2100); if(pulses!=2) $fatal(1,"second release pulse");
        $display("PASS tb_key_detect debounce_cycles=1000 pulses=2 bounce/short_press/reset/held_release=checked");
        $finish;
    end
endmodule
