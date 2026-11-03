`timescale 1ns/1ps
// C9 diagnostic APB page E0xx, separate from the pinned C2/C3 ABI.
// C2's physical map is fixed ON at reset; source RUN defaults OFF. Source
// choice can be committed only once, before any pixel stream is exposed.
module c9_live_control(
 input wire arst_n,pclk,mem_clk,video_clk,display_clk,camera_clk,phy_clk,
 input wire [7:0] paddr,input wire psel,penable,pwrite,input wire [31:0] pwdata,
 output wire pready,output reg [31:0] prdata,output reg pslverror,
 output reg source_run,pattern_mode,
 output wire pattern_valid,input wire pattern_ready,output wire [7:0] pattern_gray,
 input wire [255:0] mem_data,video_data,input wire [191:0] display_data,
 input wire [159:0] camera_data,input wire [63:0] phy_data
);
 reg busy,ready;reg [31:0] snap_sequence;reg [1:0] released;
 wire access=psel && penable;wire aligned=paddr[1:0]==0;
 wire [4:0] req_ready,reply_valid;
 wire all_req=&req_ready,all_reply=&reply_valid;
 wire start=access && pready && pwrite && paddr==8'h10 && !pslverror;
 wire release_all=access && pready && pwrite && paddr==8'h14 && !pslverror;
 wire kick=access && pready && pwrite && paddr==8'h08 && !pslverror;
 wire kick_ready;
 wire [63:0] mem_snap,vid_snap,disp_snap,cam_snap,phy_snap;
 assign pready=released[1];
 c9_snapshot_group #(.WIDTH(256)) ms(.arst_n(arst_n),.pclk(pclk),.source_clk(mem_clk),.request(start),.pair_select(pwdata[9:8]),.request_ready(req_ready[0]),.release_snapshot(release_all),.valid(reply_valid[0]),.native_data(mem_data),.snapshot(mem_snap));
 c9_snapshot_group #(.WIDTH(256)) vsnap(.arst_n(arst_n),.pclk(pclk),.source_clk(video_clk),.request(start),.pair_select(pwdata[9:8]),.request_ready(req_ready[1]),.release_snapshot(release_all),.valid(reply_valid[1]),.native_data(video_data),.snapshot(vid_snap));
 c9_snapshot_group #(.WIDTH(192)) ds(.arst_n(arst_n),.pclk(pclk),.source_clk(display_clk),.request(start),.pair_select(pwdata[9:8]),.request_ready(req_ready[2]),.release_snapshot(release_all),.valid(reply_valid[2]),.native_data(display_data),.snapshot(disp_snap));
 c9_snapshot_group #(.WIDTH(160)) cs(.arst_n(arst_n),.pclk(pclk),.source_clk(camera_clk),.request(start),.pair_select(pwdata[9:8]),.request_ready(req_ready[3]),.release_snapshot(release_all),.valid(reply_valid[3]),.native_data(camera_data),.snapshot(cam_snap));
 c9_snapshot_group #(.WIDTH(64)) ps(.arst_n(arst_n),.pclk(pclk),.source_clk(phy_clk),.request(start),.pair_select(pwdata[9:8]),.request_ready(req_ready[4]),.release_snapshot(release_all),.valid(reply_valid[4]),.native_data(phy_data),.snapshot(phy_snap));
 c2_cdc_mailbox #(.WIDTH(8)) pattern_command(.arst_n(arst_n),.s_clk(pclk),.s_valid(kick),.s_ready(kick_ready),.s_data(pwdata[7:0]),.d_clk(video_clk),.d_valid(pattern_valid),.d_ready(pattern_ready),.d_data(pattern_gray));
 always @*begin
  prdata=0;pslverror=0;
  if(!aligned)pslverror=1;
  else if(pwrite)case(paddr)
   8'h04:if(source_run || pwdata[31:16]!=16'hc9a7 || pwdata[15:2]!=0 || !pwdata[0])pslverror=1;
   8'h08:if(!source_run || !pattern_mode || !kick_ready || pwdata[31:8]!=0)pslverror=1;
   8'h10:if(busy || ready || !all_req || (pwdata&32'hfffffcff)!=1)pslverror=1;
   8'h14:if(!ready || pwdata!=1)pslverror=1;
   default:pslverror=1;
  endcase
  else case(paddr)
   8'h00:prdata=32'h43394c34;
   8'h04:prdata={29'b0,1'b1,pattern_mode,source_run};
   8'h08:prdata={31'b0,kick_ready};
   8'h10:prdata={30'b0,ready,busy};
   8'h14:prdata=snap_sequence;
   default:if(!ready)pslverror=1;
    else if(paddr==8'h40 || paddr==8'h44)prdata=mem_snap[paddr[2]*32+:32];
    else if(paddr==8'h60 || paddr==8'h64)prdata=vid_snap[paddr[2]*32+:32];
    else if(paddr==8'h80 || paddr==8'h84)prdata=disp_snap[paddr[2]*32+:32];
    else if(paddr==8'ha0 || paddr==8'ha4)prdata=cam_snap[paddr[2]*32+:32];
    else if(paddr==8'hc0 || paddr==8'hc4)prdata=phy_snap[paddr[2]*32+:32];
    else pslverror=1;
  endcase
  if(!access)pslverror=0;
 end
 always @(posedge pclk or negedge arst_n)
 if(!arst_n)begin busy<=0;ready<=0;snap_sequence<=0;source_run<=0;pattern_mode<=0;released<=0;end
 else begin
  released<={released[0],1'b1};
  if(start)begin busy<=1;snap_sequence<=snap_sequence+1;end
  if(busy && all_reply)begin busy<=0;ready<=1;end
  if(release_all)ready<=0;
  if(access && pready && pwrite && !pslverror && paddr==8'h04)begin source_run<=1;pattern_mode<=pwdata[1];end
 end
endmodule
