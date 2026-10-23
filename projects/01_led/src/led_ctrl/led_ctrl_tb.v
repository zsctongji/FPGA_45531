`timescale  1ps/1ps

module led_ctrl_tb;

  // Parameters
  localparam  LED_NUM = 4;
  localparam  LED_TIME = 100;

  //Ports
  reg  clk = 'd0;
  reg  rst_n = 'd0;
  reg  [LED_NUM-1:0] en = 'd0;

  always #10 clk = ~clk;

  initial begin
    #0 
        rst_n = 0;
        en = 4'b0000;
    # 95 
        rst_n = 1;
        en = 4'b0011;
    #1000000
        en = 4'b1111;
  end



  led_ctrl # (
    .LED_NUM(LED_NUM),
    .LED_TIME(LED_TIME)
  )
  led_ctrl_inst (
    .clk(clk),
    .rst_n(rst_n),
    .en(en),
    .led(led)
  );

//always #5  clk = ! clk ;

endmodule