`timescale 1ns/1ps
// Each domain captures one atomic bundle. The response is NOT acknowledged
// until software releases the whole snapshot, so the APB view stays frozen.
module c9_snapshot_group #(parameter WIDTH=32)(
 input wire arst_n,pclk,source_clk,request,release_snapshot,input wire [1:0] pair_select,
 output wire request_ready,valid,input wire [WIDTH-1:0] native_data,
 output wire [63:0] snapshot
);
 wire req_valid,req_ready,reply_ready;wire [1:0] requested_pair;
 wire [255:0] padded={{(256-WIDTH){1'b0}},native_data};
 c2_cdc_mailbox #(.WIDTH(2)) req(.arst_n(arst_n),.s_clk(pclk),
 .s_valid(request),.s_ready(request_ready),.s_data(pair_select),
 .d_clk(source_clk),.d_valid(req_valid),.d_ready(req_ready),.d_data(requested_pair));
 assign req_ready=reply_ready;
 c2_cdc_mailbox #(.WIDTH(64)) reply(.arst_n(arst_n),.s_clk(source_clk),
 .s_valid(req_valid && req_ready),.s_ready(reply_ready),.s_data(padded[requested_pair*64+:64]),
 .d_clk(pclk),.d_valid(valid),.d_ready(release_snapshot),.d_data(snapshot));
endmodule
