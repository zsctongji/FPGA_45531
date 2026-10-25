`timescale 1ns/1ps
// Join independent source-verdict and DDR-write completion. Neither alone may
// publish READY. One frame in flight, common reset cancels both completions.
module c2_source_fence(
 input wire clk,rst_n,start,input wire [31:0] frame_id,
 input wire writer_valid,output wire writer_ready,input wire writer_error,input wire [31:0] writer_fnv,
 input wire source_valid,output wire source_ready,input wire source_error,
 input wire [31:0] source_frame_id,source_fnv,
 output wire done_valid,input wire done_ready,output wire done_error,output wire [31:0] done_fnv
);
 reg busy,have_writer,have_source,we,se;
 reg [31:0] expected,wh,sh;
 assign writer_ready=busy && !have_writer;
 assign source_ready=busy && !have_source;
 assign done_valid=busy && have_writer && have_source;
 assign done_error=we || se || wh!=sh;
 assign done_fnv=wh;
 always @(posedge clk or negedge rst_n) begin
   if(!rst_n) begin busy<=0;have_writer<=0;have_source<=0;we<=0;se<=0;expected<=0;wh<=0;sh<=0;end
   else begin
     if(start) begin busy<=1;have_writer<=0;have_source<=0;we<=0;se<=0;expected<=frame_id;end
     if(writer_valid && writer_ready) begin have_writer<=1;we<=writer_error;wh<=writer_fnv;end
     if(source_valid && source_ready) begin
       have_source<=1;se<=source_error || source_frame_id!=expected;sh<=source_fnv;
     end
     if(done_valid && done_ready) begin busy<=0;have_writer<=0;have_source<=0;end
   end
 end
endmodule
