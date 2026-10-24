`timescale 1ns/1ps
module tb_c2_apb #(parameter P_HALF=7);
 reg arst_n=1,pclk=0,mem_clk=0,psel=0,penable=0,pwrite=0,map_enable=1;
 reg [15:0] paddr=0;reg [31:0] pwdata=0;wire [31:0] prdata;
 wire pready,pslverror,irq;
 always #(P_HALF) pclk=~pclk;always #5 mem_clk=~mem_clk;
 wire cv,cr,cs,rv,rr,rs;wire [2:0] cc;wire [1:0] status;
 wire [31:0] cg,rg,dropped;wire [511:0] descriptor;wire [3:0] states;
 reg permit=1,response_permit=1,manual=0,mv=0,ms=0;
 reg [2:0] mc=0;reg [31:0] mg=0;reg [511:0] md=0;
 wire mready,mrsp,final_rsp_ready;wire [1:0] mrstatus;wire mrslot;
 wire [31:0] mrgen;wire [511:0] mrdesc;
 assign cr=permit && !manual && mready;
 assign rv=response_permit && !manual && mrsp;
 assign status=mrstatus;assign rs=mrslot;assign rg=mrgen;assign descriptor=mrdesc;
 assign final_rsp_ready=manual?1'b1:(rr && response_permit);
 c2_apb_control dut(.arst_n(arst_n),.pclk(pclk),.mem_clk(mem_clk),
 .paddr(paddr),.psel(psel),.penable(penable),.pwrite(pwrite),.pwdata(pwdata),
 .pready(pready),.prdata(prdata),.pslverror(pslverror),.irq(irq),.map_enable(map_enable),
 .cpu_valid(cv),.cpu_ready(cr),.cpu_cmd(cc),.cpu_slot(cs),.cpu_generation(cg),
 .cpu_rsp_valid(rv),.cpu_rsp_ready(rr),.cpu_rsp_status(status),.cpu_rsp_slot(rs),
 .cpu_rsp_generation(rg),.cpu_descriptor(descriptor),.slot_states(states),.dropped(dropped),.protocol_error(1'b0));
 c2_buffer_manager pool(.clk(mem_clk),.rst_n(arst_n),
 .cmd_valid(manual?mv:(cv && permit)),.cmd_ready(mready),.cmd(manual?mc:cc),
 .slot(manual?ms:cs),.generation(manual?mg:cg),.descriptor(md),
 .rsp_valid(mrsp),.rsp_ready(final_rsp_ready),.rsp_status(mrstatus),.rsp_slot(mrslot),
 .rsp_generation(mrgen),.rsp_descriptor(mrdesc),.slot_states(states),.dropped(dropped));
 integer checks=0,commands=0,i;reg [31:0] value;
 task apb(input bit wr,input [15:0] address,input [31:0] data,input bit error);
 begin
   @(negedge pclk);paddr=address;pwdata=data;pwrite=wr;psel=1;penable=0;
   @(negedge pclk);penable=1;
   do @(posedge pclk);while(!pready);
   if(pslverror!==error) $fatal(1,"APB error response addr=%h got=%b",address,pslverror);
   value=prdata;checks=checks+1;
   @(negedge pclk);psel=0;penable=0;pwrite=0;
 end
 endtask
 task wait_done;
 begin
   apb(0,8,0,0);
   while(value!=2) apb(0,8,0,0);
   if(!irq) $fatal(1,"Missing DONE IRQ");
 end
 endtask
 task manual_command(input [2:0] op,input [31:0] gen);
 begin
   @(negedge mem_clk);manual=1;mv=1;mc=op;mg=gen;
   do @(posedge mem_clk);while(!mready);
   @(negedge mem_clk);mv=0;
   while(!mrsp) @(negedge mem_clk);
   if(mrstatus!=0) $fatal(1,"Fixture manual command failed");
   @(negedge mem_clk);manual=0;
 end
 endtask
 task exchange(input [2:0] op,input [31:0] gen,input [1:0] expected);
 begin
   apb(1,16'h10,gen,0);apb(1,16'h0c,{29'b0,op},0);commands=commands+1;
   wait_done;apb(0,16'h18,0,0);
   if(value!=expected) $fatal(1,"APB ownership status mismatch");
   apb(1,16'h14,1,0);
 end
 endtask
 initial begin
   #1;arst_n=0;#(P_HALF*4+23);arst_n=1;
   md=0;md[31:0]=32'h10000;md[63:32]=123;md[159:128]=32'h1000;
   md[191:160]=9216;md[223:192]=1;md[255:224]=96;md[319:288]=1;
   manual_command(0,0);manual_command(1,1);
   apb(0,0,0,0);if(value!=32'h43325332) $fatal(1,"Wrong identity");
   apb(0,4,0,0);if(value!=32'h20000) $fatal(1,"Wrong version");
   apb(0,16'h30,0,0);if(value!=32'h09010000) $fatal(1,"Wrong static map");
   apb(1,16'h14,1,1);apb(1,16'h0c,0,1);
   apb(0,16'h1000,0,1);apb(0,2,0,1);apb(1,16'h40,0,1);
   map_enable=0;apb(1,16'h0c,5,1);map_enable=1;
   // Setup phase alone cannot enqueue a command.
   @(negedge pclk);paddr=12;pwdata=5;pwrite=1;psel=1;penable=0;
   repeat(8) @(negedge pclk);
   if(dut.busy || cv) $fatal(1,"Command executed in APB setup phase");
   psel=0;pwrite=0;
   permit=0;apb(1,16'h0c,5,0);commands=commands+1;
   repeat(20) @(negedge pclk);
   apb(0,8,0,0);if(value!=1) $fatal(1,"BUSY not held across CDC/backpressure");
   apb(1,16'h10,9,1);apb(1,12,5,1);
   response_permit=0;permit=1;
   repeat(20) @(negedge pclk);
   apb(0,8,0,0);if(value!=1) $fatal(1,"Response backpressure lost");
   response_permit=1;wait_done;
   apb(0,16'h1c,0,0);if(value!=1) $fatal(1,"QUERY generation lost");
   apb(0,16'h44,0,0);if(value!=123) $fatal(1,"Descriptor word order wrong");
   // Underlying slot changes while APB response remains an immutable snapshot.
   manual_command(3,1);manual_command(4,1);manual_command(0,0);
   md[63:32]=124;manual_command(1,2);
   repeat(16) begin
     apb(0,16'h44,0,0);if(value!=123) $fatal(1,"Torn APB response snapshot");
   end
   apb(1,16'h0c,5,1);apb(1,16'h14,1,0);
   exchange(3,1,2);exchange(3,2,0);exchange(4,2,0);
   for(i=0;i<100;i=i+1) exchange(5,0,0);
   // Common reset cancels an outstanding command and all reply ownership.
   permit=0;apb(1,12,5,0);
   @(negedge pclk);arst_n=0;#(P_HALF*4+23);arst_n=1;permit=1;
   repeat(20) @(negedge pclk);
   apb(0,8,0,0);if(value || irq || states || cv) $fatal(1,"Ghost APB state after reset");
   exchange(5,0,0);
   $display("PASS tb_c2_apb commands=%0d checks=%0d APB3 CDC setup errors busy immutable_snapshot stale_token common_reset",commands,checks);
   $finish;
 end
 initial begin #10000000;$fatal(1,"APB timeout");end
endmodule
