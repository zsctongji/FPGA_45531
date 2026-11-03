`timescale 1ns/1ps
// A raster timing/GRAY8 boundaries; C2 owns the only DDR controller.
module c2_video_pipeline #(parameter integer WIDTH=1920,HEIGHT=1080)(
input wire arst_n,mem_clk,video_clk,display_clk,enable,time_valid,
input wire pixel_vs,pixel_de,input wire [7:0] pixel_gray,
input wire [31:0] now_ms,source_frames,
input wire record_valid,record_complete,input wire [31:0] record_id,record_ms,
input wire display_vs,display_de,display_hs,
output wire [23:0] display_rgb,output wire out_vs,out_de,out_hs,
output wire display_busy,display_available,display_failed,
output wire [31:0] display_frame_id,display_timestamp_ms,
output wire [31:0] published,dropped,overflow_frames,write_errors,read_errors,
output wire [31:0] repeated,empty_scans,underflows,missed_scans,completed_scans,max_aw_wait,max_ar_wait,
output wire awvalid,
input wire awready,
output wire [31:0] awaddr,
output wire [7:0] awlen,
output wire wvalid,
input wire wready,
output wire [127:0] wdata,
output wire [15:0] wstrb,
output wire wlast,
input wire bvalid,
output wire bready,
input wire [1:0] bresp,
output wire arvalid,
input wire arready,
output wire [31:0] araddr,
output wire [7:0] arlen,
input wire rvalid,
output wire rready,
input wire [127:0] rdata,
input wire rlast,
input wire [1:0] rresp
);
localparam integer STRIDE=((WIDTH+15)/16)*16;
localparam integer PITCH=((STRIDE*HEIGHT+4095)/4096)*4096;
localparam LAYOUT_OK=WIDTH>=16 && WIDTH<=65535 && HEIGHT>0 && HEIGHT<=65535 && PITCH>0 && PITCH<=5591040;
wire safe_enable=enable && LAYOUT_OK;
wire iv,ir,ov,orr,sv,sr;wire [129:0] idata,odata;
c2_video_ingress #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) ingress(
.arst_n(arst_n),.video_clk(video_clk),.mem_clk(mem_clk),.enable(safe_enable),.time_valid(time_valid),
.vs(pixel_vs),.de(pixel_de),.gray(pixel_gray),.now_ms(now_ms),.source_frames(source_frames),
.record_valid(record_valid),.record_complete(record_complete),.record_id(record_id),.record_ms(record_ms),
.valid(iv),.ready(ir),.data(idata),.overflow_frames(overflow_frames));
c2_video_framebuffer #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) framebuffer(
.arst_n(arst_n),.clk(mem_clk),.display_clk(display_clk),.enable(safe_enable),
.in_valid(iv),.in_ready(ir),.in_data(idata),.scan_valid(sv),.scan_ready(sr),
.out_valid(ov),.out_ready(orr),.out_data(odata),
.published(published),.dropped(dropped),.write_errors(write_errors),.read_errors(read_errors),
.repeated(repeated),.empty_scans(empty_scans),.max_aw_wait(max_aw_wait),.max_ar_wait(max_ar_wait),.bank_states(),
.awvalid(awvalid),
.awready(awready),
.awaddr(awaddr),
.awlen(awlen),
.wvalid(wvalid),
.wready(wready),
.wdata(wdata),
.wstrb(wstrb),
.wlast(wlast),
.bvalid(bvalid),
.bready(bready),
.bresp(bresp),
.arvalid(arvalid),
.arready(arready),
.araddr(araddr),
.arlen(arlen),
.rvalid(rvalid),
.rready(rready),
.rdata(rdata),
.rlast(rlast),
.rresp(rresp));
c2_video_scanout #(.WIDTH(WIDTH),.HEIGHT(HEIGHT)) scanout(
.arst_n(arst_n),.clk(display_clk),.vs(display_vs),.de(display_de),.hs(display_hs),
.scan_valid(sv),.scan_ready(sr),.in_valid(ov),.in_ready(orr),.in_data(odata),
.rgb(display_rgb),.out_vs(out_vs),.out_de(out_de),.out_hs(out_hs),
.busy(display_busy),.frame_available(display_available),.frame_failed(display_failed),
.frame_id(display_frame_id),.timestamp_ms(display_timestamp_ms),.underflows(underflows),
.missed_scans(missed_scans),.completed_scans(completed_scans));
endmodule
