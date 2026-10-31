//***************************************************************/
//
// Moudel Name    : ddr3_example_top.v
// Version        : 1.1
// Date Created   : 2023-02-23 10:37:59
// Last Modified  : 2023-02-24 15:27:41
// Abstract       : ---
//
//***************************************************************/
//Modification History
//1.initial
//***************************************************************/
`include "C:/Users/16034/Downloads/FPGA/FPGA_2026_T3_P3/projects/03_tinyml/src/ddr3_controller/ddr3_parameter.vh"
`include "C:/Users/16034/Downloads/FPGA/FPGA_2026_T3_P3/projects/03_tinyml/src/define.v"
`include "C:/Users/16034/Downloads/FPGA/FPGA_2026_T3_P3/projects/03_tinyml/src/tinyml/defines.v"
module c2_tinyml_soc_top #
(
parameter integer C2_FRAME_WIDTH=1920,C2_FRAME_HEIGHT=1080,C2_STEP_X=20,C2_STEP_Y=20,
parameter                       RANK_RATIO         = 1,       // # of unique CS outputs per rank
parameter                       CK_RATIO           = `CK_RATIO, 
parameter                       ASYN_AXI_CLK       = `ASYN_AXI_CLK, 
parameter                       RANKS              = `RANKS,
parameter                       CK_WIDTH           = `CK_WIDTH,       // # of CK/CK# outputs to memory   
parameter                       CKE_WIDTH          = `CKE_WIDTH,       // # of cke outputs
parameter                       CS_WIDTH           = `CS_WIDTH,       // # of unique CS outputs
parameter                       BANK_WIDTH         = `BANK_WIDTH,       // # of bank bits
parameter                       ROW_WIDTH          = `ROW_WIDTH,       // DRAM address bus width
parameter                       COL_WIDTH          = `COL_WIDTH,      // column address width
parameter                       DM_WIDTH           = `DM_WIDTH,       // # of DM (data mask)
parameter                       DQS_WIDTH          = `DQS_WIDTH,       // # of DQS (strobe)
parameter                       DQ_WIDTH           = `DQ_WIDTH,      // # of DQ (data)
parameter                       ODT_WIDTH          = `ODT_WIDTH,
parameter                       DQ_CNT_WIDTH       = `DQ_CNT_WIDTH,       // = ceil(log2(DQ_WIDTH))
parameter                       DQS_CNT_WIDTH      = `DQS_CNT_WIDTH,       // = ceil(log2(DQS_WIDTH))  
parameter                       DRAM_WIDTH         = `DRAM_WIDTH,       // # of DQ per DQS   
parameter                       DATA_WIDTH         = `DATA_WIDTH,
parameter                       ADDR_WIDTH         = `ADDR_WIDTH,    
parameter                       AXI_ID_WIDTH       = `AXI_ID_WIDTH,
parameter                       AXI_ADDR_WIDTH     = `AXI_ADDR_WIDTH,
parameter                       AXI_DATA_WIDTH     = `AXI_DATA_WIDTH
)
(

input wire c2_video_clk,c2_map_enable,
output wire system_spi_0_io_sclk_write,system_spi_0_io_ss,
input wire system_spi_0_io_data_0_read,
output wire system_spi_0_io_data_0_write,system_spi_0_io_data_0_writeEnable,
input wire system_spi_0_io_data_1_read,
output wire system_spi_0_io_data_1_write,system_spi_0_io_data_1_writeEnable,
input wire system_spi_0_io_data_2_read,
output wire system_spi_0_io_data_2_write,system_spi_0_io_data_2_writeEnable,
input wire system_spi_0_io_data_3_read,
output wire system_spi_0_io_data_3_write,system_spi_0_io_data_3_writeEnable,
input wire c2_pixel_vs,c2_pixel_de,
input wire [7:0] c2_pixel_gray,
output wire c2_capture_config_valid,c2_capture_record_valid,c2_capture_record_complete,
output wire [31:0] c2_capture_record_frame_id,c2_capture_record_timestamp_ms,
output wire [15:0] c2_capture_record_width,c2_capture_record_height,
output wire [31:0] c2_capture_source_frames,c2_capture_format_errors,
output wire [31:0] c2_shared_video_ms,
output wire c2_shared_video_valid,
output wire [31:0] c2_a_completed,c2_a_rejected,c2_a_source_faults,
input wire c2_display_clk,c2_display_vs,c2_display_de,c2_display_hs,
output wire [23:0] c2_display_rgb,
output wire c2_out_vs,c2_out_de,c2_out_hs,c2_display_busy,c2_display_available,c2_display_failed,
output wire [31:0] c2_display_frame_id,c2_display_timestamp_ms,
output wire [31:0] c2_video_published,c2_video_dropped,c2_video_overflow_frames,
output wire [31:0] c2_video_write_errors,c2_video_read_errors,c2_video_underflows,
output wire [31:0] c2_video_repeated,c2_video_empty_scans,c2_video_missed_scans,c2_video_completed_scans,
output wire [31:0] c2_video_max_aw_wait,c2_video_max_ar_wait,
input wire c3_io_enable,c3_sensor_scl_read,c3_sensor_sda_read,
output wire c3_sensor_scl_drive_low,c3_sensor_sda_drive_low,c3_buzzer,c3_alarm_led,
   // Clock and reset ports
   input                              axi_clk,      
   input                              core_clk,     // CORE CLK @ 100MHz
   input                              sdram_clk,    // SDRAM CK @ 400MHz
   input                              rx_cal_clk,   // SDRAM CK @ 400MHz
   input                              tx_cal_clk,   // SDRAM CK @ 400MHz
   input                              tx_cal_clk_90edge,   // SDRAM CK @ 400MHz
   input                              pll_locked,
   input                              user_pll_locked,
   input                              i_sysclk,
   input                              i_peripheralClk,
   input                              i_fb_clk,
   //&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
   output  wire                       system_uart_0_io_txd,
   input                              system_uart_0_io_rxd,   
    // debug core ports
`ifdef  Efinity_Debug  //&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& 
`ifdef RISCV_SOFT_JTAG
  input                               io_jtag_tms,
  input                               io_jtag_tdi,
  output  wire                        io_jtag_tdo,
  input                               io_jtag_tck,
`else
`endif 
  input                               jtag_inst1_CAPTURE ,
  input                               jtag_inst1_DRCK    ,
  input                               jtag_inst1_RESET   ,
  input                               jtag_inst1_RUNTEST ,
  input                               jtag_inst1_SEL     ,
  input                               jtag_inst1_SHIFT   ,
  input                               jtag_inst1_TCK     ,
  input                               jtag_inst1_TDI     ,
  input                               jtag_inst1_TMS     ,
  input                               jtag_inst1_UPDATE  ,
  output                              jtag_inst1_TDO     ,
`endif  //&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
   // PLL status flags  
   output [2:0]                       pll_shift,  
   output [4:0]                       pll_shift_sel,
   output                             pll_shift_ena,  
   // memory interface ports
   output                             ddr_ck_hi,
   output                             ddr_ck_lo,
   output                             ddr_reset_n,
   output [CKE_WIDTH-1:0]             ddr_cke,     
   output [ROW_WIDTH-1:0]             ddr_addr,
   output [BANK_WIDTH-1:0]            ddr_ba,
   output                             ddr_cas_n,

   output [CS_WIDTH*RANK_RATIO-1:0]   ddr_cs_n,
   output                             ddr_ras_n,
   output                             ddr_we_n,
   
   input  [DQS_WIDTH-1:0]             ddr_dqs_in_hi,
   input  [DQS_WIDTH-1:0]             ddr_dqs_in_lo,
   input  [DQ_WIDTH-1:0]              ddr_dq_in_hi,
   input  [DQ_WIDTH-1:0]              ddr_dq_in_lo,
   
   output [DQS_WIDTH-1:0]             ddr_dqs_oe,
   output [DQS_WIDTH-1:0]             ddr_dqs_oe_n,
   output [DQ_WIDTH-1:0]              ddr_dq_oe,  
   output [DQS_WIDTH-1:0]             ddr_dqs_out_hi,
   output [DQS_WIDTH-1:0]             ddr_dqs_out_lo,
   output [DQ_WIDTH-1:0]              ddr_dq_out_hi,
   output [DQ_WIDTH-1:0]              ddr_dq_out_lo,
   output [DM_WIDTH-1:0]              ddr_dm_hi,
   output [DM_WIDTH-1:0]              ddr_dm_lo,
   output [ODT_WIDTH-1:0]             ddr_odt

   );


      
//Parameter Define
localparam FREQ = 200;			// default is 100 MHz.  Redefine as needed.
`ifndef SIM
    localparam CNT_INIT = 1.5*FREQ*1000;
`else
    localparam CNT_INIT = 10;
`endif    
  localparam   AIW               = AXI_ID_WIDTH      ;
  localparam   ADW               = AXI_DATA_WIDTH    ;
  localparam   ABN               = AXI_DATA_WIDTH/8   ;
  /////////////////////////////////////////////////////////
  // Wire declarations
  reg  [19:0]                       cnt;    
  wire                              clk;
  wire                              rst;
  wire                              mmcm_locked;
  reg                               aresetn;
  wire                              app_sr_active;
  wire                              app_ref_ack;
  wire                              app_zq_ack;

  wire                              cal_done;


//Custom instruction
wire                    cpu_customInstruction_cmd_valid;
wire                    cpu_customInstruction_cmd_ready;
wire  [9:0]             cpu_customInstruction_function_id;
wire  [31:0]            cpu_customInstruction_inputs_0;
wire  [31:0]            cpu_customInstruction_inputs_1;
wire                    cpu_customInstruction_rsp_valid;
wire                    cpu_customInstruction_rsp_ready;
wire  [31:0]            cpu_customInstruction_outputs_0;
wire                    cpu_customInstruction_cmd_int;
wire                    userInterruptA;

localparam AXI_TINYML_DATA_WIDTH = 128;

wire [7:0]              axi_inter_s0_awid;
wire [31:0]             axi_inter_s0_awaddr;
wire [7:0]              axi_inter_s0_awlen;
wire [2:0]              axi_inter_s0_awsize;
wire [1:0]              axi_inter_s0_awburst;
wire                    axi_inter_s0_awlock;
wire [3:0]              axi_inter_s0_awcache;
wire [2:0]              axi_inter_s0_awprot;
wire [3:0]              axi_inter_s0_awqos;
wire                    axi_inter_s0_awvalid;
wire                    axi_inter_s0_awready;
wire [127:0]            axi_inter_s0_wdata;
wire [15:0]             axi_inter_s0_wstrb;
wire                    axi_inter_s0_wlast;
wire                    axi_inter_s0_wvalid;
wire                    axi_inter_s0_wready;
wire [7:0]              axi_inter_s0_bid;
wire [1:0]              axi_inter_s0_bresp;
wire                    axi_inter_s0_bvalid;
wire                    axi_inter_s0_bready;
wire [7:0]              axi_inter_s0_arid;
wire [31:0]             axi_inter_s0_araddr;
wire [7:0]              axi_inter_s0_arlen;
wire [2:0]              axi_inter_s0_arsize;
wire [1:0]              axi_inter_s0_arburst;
wire                    axi_inter_s0_arlock;
wire [3:0]              axi_inter_s0_arcache;
wire [2:0]              axi_inter_s0_arprot;
wire [3:0]              axi_inter_s0_arqos;
wire                    axi_inter_s0_arvalid;
wire                    axi_inter_s0_arready;
wire [7:0]              axi_inter_s0_rid;
wire [127:0]            axi_inter_s0_rdata;
wire [1:0]              axi_inter_s0_rresp;
wire                    axi_inter_s0_rlast;
wire                    axi_inter_s0_rvalid;
wire                    axi_inter_s0_rready;

wire [7:0]              axi_inter_s1_awid;
wire [31:0]             axi_inter_s1_awaddr;
wire [7:0]              axi_inter_s1_awlen;
wire [2:0]              axi_inter_s1_awsize;
wire [1:0]              axi_inter_s1_awburst;
wire                    axi_inter_s1_awlock;
wire [3:0]              axi_inter_s1_awcache;
wire [2:0]              axi_inter_s1_awprot;
wire [3:0]              axi_inter_s1_awqos;
wire                    axi_inter_s1_awvalid;
wire                    axi_inter_s1_awready;
wire [127:0]            axi_inter_s1_wdata;
wire [15:0]             axi_inter_s1_wstrb;
wire                    axi_inter_s1_wlast;
wire                    axi_inter_s1_wvalid;
wire                    axi_inter_s1_wready;
wire [7:0]              axi_inter_s1_bid;
wire [1:0]              axi_inter_s1_bresp;
wire                    axi_inter_s1_bvalid;
wire                    axi_inter_s1_bready;
wire [7:0]              axi_inter_s1_arid;
wire [31:0]             axi_inter_s1_araddr;
wire [7:0]              axi_inter_s1_arlen;
wire [2:0]              axi_inter_s1_arsize;
wire [1:0]              axi_inter_s1_arburst;
wire                    axi_inter_s1_arlock;
wire [3:0]              axi_inter_s1_arcache;
wire [2:0]              axi_inter_s1_arprot;
wire [3:0]              axi_inter_s1_arqos;
wire                    axi_inter_s1_arvalid;
wire                    axi_inter_s1_arready;
wire [7:0]              axi_inter_s1_rid;
wire [127:0]            axi_inter_s1_rdata;
wire [1:0]              axi_inter_s1_rresp;
wire                    axi_inter_s1_rlast;
wire                    axi_inter_s1_rvalid;
wire                    axi_inter_s1_rready;

wire [7:0]              axi_inter_s2_awid;
wire [31:0]             axi_inter_s2_awaddr;
wire [7:0]              axi_inter_s2_awlen;
wire [2:0]              axi_inter_s2_awsize;
wire [1:0]              axi_inter_s2_awburst;
wire [1:0] axi_inter_s2_awlock;
wire [3:0]              axi_inter_s2_awcache;
wire [2:0]              axi_inter_s2_awprot;
wire [3:0]              axi_inter_s2_awqos;
wire                    axi_inter_s2_awvalid;
wire                    axi_inter_s2_awready;
wire [AXI_TINYML_DATA_WIDTH-1:0]            axi_inter_s2_wdata;
wire [AXI_TINYML_DATA_WIDTH/8-1:0]             axi_inter_s2_wstrb;
wire                    axi_inter_s2_wlast;
wire                    axi_inter_s2_wvalid;
wire                    axi_inter_s2_wready;
wire [7:0]              axi_inter_s2_bid;
wire [1:0]              axi_inter_s2_bresp;
wire                    axi_inter_s2_bvalid;
wire                    axi_inter_s2_bready;
wire [7:0]              axi_inter_s2_arid;
wire [31:0]             axi_inter_s2_araddr;
wire [7:0]              axi_inter_s2_arlen;
wire [2:0]              axi_inter_s2_arsize;
wire [1:0]              axi_inter_s2_arburst;
wire [1:0] axi_inter_s2_arlock;
wire [3:0]              axi_inter_s2_arcache;
wire [2:0]              axi_inter_s2_arprot;
wire [3:0]              axi_inter_s2_arqos;
wire                    axi_inter_s2_arvalid;
wire                    axi_inter_s2_arready;
wire [7:0]              axi_inter_s2_rid;
wire [AXI_TINYML_DATA_WIDTH-1:0]            axi_inter_s2_rdata;
wire [1:0]              axi_inter_s2_rresp;
wire                    axi_inter_s2_rlast;
wire                    axi_inter_s2_rvalid;
wire                    axi_inter_s2_rready;

wire [7:0]              axi_inter_m_awid;
wire [31:0]             axi_inter_m_awaddr;
wire [7:0]              axi_inter_m_awlen;
wire [2:0]              axi_inter_m_awsize;
wire [1:0]              axi_inter_m_awburst;
wire                    axi_inter_m_awlock;
wire [3:0]              axi_inter_m_awcache;
wire [2:0]              axi_inter_m_awprot;
wire [3:0]              axi_inter_m_awqos;
wire [3:0]              axi_inter_m_awregion;
wire                    axi_inter_m_awvalid;
wire                    axi_inter_m_awready;
wire [127:0]            axi_inter_m_wdata;
wire [15:0]             axi_inter_m_wstrb;
wire                    axi_inter_m_wlast;
wire                    axi_inter_m_wvalid;
wire                    axi_inter_m_wready;
wire [7:0]              axi_inter_m_bid;
wire [1:0]              axi_inter_m_bresp;
wire                    axi_inter_m_bvalid;
wire                    axi_inter_m_bready;
wire [7:0]              axi_inter_m_arid;
wire [31:0]             axi_inter_m_araddr;
wire [7:0]              axi_inter_m_arlen;
wire [2:0]              axi_inter_m_arsize;
wire [1:0]              axi_inter_m_arburst;
wire                    axi_inter_m_arlock;
wire [3:0]              axi_inter_m_arcache;
wire [2:0]              axi_inter_m_arprot;
wire [3:0]              axi_inter_m_arqos;
wire [3:0]              axi_inter_m_arregion;
wire                    axi_inter_m_arvalid;
wire                    axi_inter_m_arready;
wire [7:0]              axi_inter_m_rid;
wire [127:0]            axi_inter_m_rdata;
wire [1:0]              axi_inter_m_rresp;
wire                    axi_inter_m_rlast;
wire                    axi_inter_m_rvalid;
wire                    axi_inter_m_rready;

  wire                              ddr_reset; 
  wire                              sys_rst;
  wire  [2:0]                       phy_wr_pll_shift;
  wire                              idelay_ld       ;
  wire                              mpr_rdlvl_dly   ;
  wire  [7:0]                       wrlvl_dq_check  ;
  wire  [7:0]                       rd_level_dqs_check;  
  wire  [2:0]                       rdlvl_shift;  
  wire  [2:0]                       wrlvl_shift;  
  wire  [15:0]                      debug_fifo;  
  wire  [15:0]                      overflow_fifo;  
  wire  [6:0]                       init_cur_state;  
  wire  [35:0]                      ddr_debug_port;  
  wire                              app_rdy;  
  wire                              user_clk;  
  wire                              ddr_rstn;  

  
// Start of User Design top instance
//***************************************************************************
// The User design is instantiated below. The memory interface ports are
// connected to the top-level and the application interface ports are
// connected to the traffic generator module. This provides a reference
// for connecting the memory controller to system.
//***************************************************************************
always @(posedge user_clk or negedge sys_rst) begin
	if (!sys_rst)
		cnt <= 0;
    else if (cnt != CNT_INIT) 
        cnt <= cnt + 20'd1;
	else 
        cnt <= cnt;
end
assign ddr_rstn = (cnt == CNT_INIT);


generate
if (ASYN_AXI_CLK) begin
assign user_clk = axi_clk;

end else begin
assign user_clk = core_clk;
end
endgenerate
//***************************************************************************
// The traffic generation module instantiated below drives traffic (patterns)
// on the application interface of the memory controller
//***************************************************************************
//***************************************************************************

assign sys_rst       = pll_locked & user_pll_locked;

//***************************************************************************
ddr3_top #(.AXI_ID_WIDTH(8)) u_ddr3_top
      (
      
    .axi_clk                (axi_clk             ),
    .core_clk               (core_clk            ),
    .sdram_clk              (sdram_clk           ),  
    .rx_cal_clk             (rx_cal_clk          ),
    .tx_cal_clk             (tx_cal_clk          ),
    .tx_cal_clk_90edge      (tx_cal_clk_90edge   ),
    .rstn                   (ddr_rstn            ),      
    .pll_shift              (pll_shift           ),
    .pll_shift_sel          (pll_shift_sel       ),
    .pll_shift_ena          (pll_shift_ena       ), 
///////////////DDR BUS
    .ddr_ck_hi              (ddr_ck_hi           ),
    .ddr_ck_lo              (ddr_ck_lo           ),
    .ddr_cke                (ddr_cke             ),    
    .ddr_reset_n            (ddr_reset_n         ),
    .ddr_cs_n               (ddr_cs_n            ),
    .ddr_ras_n              (ddr_ras_n           ),
    .ddr_cas_n              (ddr_cas_n           ),
    .ddr_we_n               (ddr_we_n            ),     
    .ddr_addr               (ddr_addr            ),
    .ddr_ba                 (ddr_ba              ),

    .ddr_dqs_oe             (ddr_dqs_oe          ),
    .ddr_dqs_oe_n           (ddr_dqs_oe_n        ),
    .ddr_dq_oe              (ddr_dq_oe           ),
    .ddr_dqs_in_hi          (ddr_dqs_in_hi       ),
    .ddr_dqs_in_lo          (ddr_dqs_in_lo       ),
    .ddr_dq_in_hi           (ddr_dq_in_hi        ),
    .ddr_dq_in_lo           (ddr_dq_in_lo        ),

    .ddr_dqs_out_hi         (ddr_dqs_out_hi      ),
    .ddr_dqs_out_lo         (ddr_dqs_out_lo      ),
    .ddr_dq_out_hi          (ddr_dq_out_hi       ),
    .ddr_dq_out_lo          (ddr_dq_out_lo       ),
    
    .ddr_dm_hi              (ddr_dm_hi           ),
    .ddr_dm_lo              (ddr_dm_lo           ),
    .ddr_odt                (ddr_odt             ),

// Application interface ports
       .app_sr_req                     (1'b0),
       .app_ref_req                    (1'b0),
       .app_zq_req                     (1'b0),
       .app_sr_active                  (app_sr_active),
       .app_ref_ack                    (app_ref_ack),
       .app_zq_ack                     (app_zq_ack),

// Slave Interface Write Address Ports
       .s_axi_awid                     (axi_inter_m_awid        ),
       .s_axi_awaddr                   (axi_inter_m_awaddr      ),
       .s_axi_awlen                    (axi_inter_m_awlen       ),
       .s_axi_awsize                   (axi_inter_m_awsize      ),
       .s_axi_awburst                  (axi_inter_m_awburst     ),
       .s_axi_awlock                   (axi_inter_m_awlock      ),
       .s_axi_awcache                  (axi_inter_m_awcache     ),
       .s_axi_awprot                   (axi_inter_m_awprot      ),
       .s_axi_awqos                    (axi_inter_m_awqos       ),
       .s_axi_awvalid                  (axi_inter_m_awvalid     ),
       .s_axi_awready                  (axi_inter_m_awready     ),
// Slave Interface Write Data Ports
       .s_axi_wdata                    (axi_inter_m_wdata       ),
       .s_axi_wstrb                    (axi_inter_m_wstrb       ),
       .s_axi_wlast                    (axi_inter_m_wlast       ),
       .s_axi_wvalid                   (axi_inter_m_wvalid      ),
       .s_axi_wready                   (axi_inter_m_wready      ),
// Slave Interface Write Response Ports
       .s_axi_bid                      (axi_inter_m_bid         ),
       .s_axi_bresp                    (axi_inter_m_bresp       ),
       .s_axi_bvalid                   (axi_inter_m_bvalid      ),
       .s_axi_bready                   (axi_inter_m_bready      ),
// Slave Interface Read Address Ports
       .s_axi_arid                     (axi_inter_m_arid        ),
       .s_axi_araddr                   (axi_inter_m_araddr      ),
       .s_axi_arlen                    (axi_inter_m_arlen       ),
       .s_axi_arsize                   (axi_inter_m_arsize      ),
       .s_axi_arburst                  (axi_inter_m_arburst     ),
       .s_axi_arlock                   (axi_inter_m_arlock      ),
       .s_axi_arcache                  (axi_inter_m_arcache     ),
       .s_axi_arprot                   (axi_inter_m_arprot      ),
       .s_axi_arqos                    (axi_inter_m_arqos              ),
       .s_axi_arvalid                  (axi_inter_m_arvalid     ),
       .s_axi_arready                  (axi_inter_m_arready     ),
// Slave Interface Read Data Ports
       .s_axi_rid                      (axi_inter_m_rid         ),
       .s_axi_rdata                    (axi_inter_m_rdata       ),
       .s_axi_rresp                    (axi_inter_m_rresp       ),
       .s_axi_rlast                    (axi_inter_m_rlast       ),
       .s_axi_rvalid                   (axi_inter_m_rvalid      ),
       .s_axi_rready                   (axi_inter_m_rready      ),
//DEBUG       
       .wrlvl_dq_check                 (wrlvl_dq_check    ) ,
       .rd_level_dqs_check             (rd_level_dqs_check) ,
       .rdlvl_shift                    (rdlvl_shift) ,
       .wrlvl_shift                    (wrlvl_shift) ,
       .init_cur_state                 (init_cur_state    ) ,
       .idelay_ld                      (idelay_ld         ) ,
       .mpr_rdlvl_dly                  (mpr_rdlvl_dly     ) ,
       .ddr_debug_port                 (ddr_debug_port    ) ,
       .cal_done                       (cal_done          ) 
       );
// End of User Design top instance

//***************************************************************************

//***************************************************************************
wire [15:0] apb_paddr;
wire [31:0] apb_pwdata,apb_prdata;
wire apb_psel,apb_penable,apb_pready,apb_pwrite,apb_pslverror;
wire c2_irq,c2_protocol_error,c2_cpu_rejected,c2_cpu_protocol_error;
wire c2_peripheral_reset;
reg [1:0] c2_mem_release;
always @(posedge io_memoryClk or posedge io_systemReset)
 if(io_systemReset) c2_mem_release<=0;else c2_mem_release<={c2_mem_release[0],1'b1};
wire userInterruptB;
assign userInterruptB=c2_irq;
wire c3_page=apb_paddr[15:8]==8'h10;
wire [31:0] c2_apb_prdata,c3_apb_prdata,c3_shared_ms;
wire c2_apb_ready,c3_apb_ready,c2_apb_error,c3_apb_error,c3_shared_valid;
assign apb_prdata=c3_page?c3_apb_prdata:c2_apb_prdata;
assign apb_pready=c3_page?c3_apb_ready:c2_apb_ready;
assign apb_pslverror=c3_page?c3_apb_error:c2_apb_error;

assign axi_inter_m_awqos=4'b0;
assign axi_inter_m_arqos=4'b0;
wire io_systemReset;
wire io_memoryClk;
assign io_memoryClk = user_clk;
assign userInterruptA = cpu_customInstruction_cmd_int;

//wire io_memoryReset;
sapphire_soc u_sapphire_soc(
    .io_asyncReset                      (!cal_done                        ),
    .io_systemClk                       (i_sysclk                           ),

    //UART 0
    .system_uart_0_io_txd               (system_uart_0_io_txd               ),
    .system_uart_0_io_rxd               (system_uart_0_io_rxd               ),
    .io_memoryClk                       (user_clk                           ),
    .io_memoryReset                     (                                   ),
    .io_systemReset                     (io_systemReset                                   ),
    .io_peripheralClk                   (i_peripheralClk                      ),
    .io_peripheralReset                 (c2_peripheral_reset),    
    //External Memory AXI4 Interface
    .io_ddrA_aw_payload_prot            (                                  ),
    .io_ddrA_aw_payload_qos             (                                  ),
    .io_ddrA_aw_payload_cache           (                                  ),
    .io_ddrA_aw_payload_lock            (axi_inter_s0_awlock                     ),
    .io_ddrA_aw_payload_burst           (axi_inter_s0_awburst                    ),
    .io_ddrA_aw_payload_size            (axi_inter_s0_awsize                     ),
    .io_ddrA_aw_payload_len             (axi_inter_s0_awlen                      ),
    .io_ddrA_aw_payload_region          (                                  ),
    .io_ddrA_aw_payload_id              (axi_inter_s0_awid                       ),
    .io_ddrA_aw_payload_addr            (axi_inter_s0_awaddr                     ),
    .io_ddrA_aw_ready                   (axi_inter_s0_awready                    ),
    .io_ddrA_aw_valid                   (axi_inter_s0_awvalid                    ),

    .io_ddrA_w_payload_last             (axi_inter_s0_wlast                      ),
    .io_ddrA_w_ready                    (axi_inter_s0_wready                     ),
    .io_ddrA_w_valid                    (axi_inter_s0_wvalid                     ),    
    .io_ddrA_w_payload_strb             (axi_inter_s0_wstrb                      ),
    .io_ddrA_w_payload_data             (axi_inter_s0_wdata                      ),

    .io_ddrA_b_payload_resp             (axi_inter_s0_bresp),
    .io_ddrA_b_payload_id               (axi_inter_s0_bid                        ),
    .io_ddrA_b_ready                    (axi_inter_s0_bready                     ),
    .io_ddrA_b_valid                    (axi_inter_s0_bvalid                     ),

    .io_ddrA_ar_payload_prot            (                                  ),
    .io_ddrA_ar_payload_qos             (                                  ),
    .io_ddrA_ar_payload_cache           (                                  ),
    .io_ddrA_ar_payload_region          (                                  ),
    .io_ddrA_ar_payload_lock            (axi_inter_s0_arlock                     ),
    .io_ddrA_ar_payload_burst           (axi_inter_s0_arburst                    ),
    .io_ddrA_ar_payload_size            (axi_inter_s0_arsize                     ),
    .io_ddrA_ar_payload_len             (axi_inter_s0_arlen                      ),
    .io_ddrA_ar_payload_id              (axi_inter_s0_arid                       ),
    .io_ddrA_ar_payload_addr            (axi_inter_s0_araddr                     ),
    .io_ddrA_ar_ready                   (axi_inter_s0_arready                    ),
    .io_ddrA_ar_valid                   (axi_inter_s0_arvalid                    ),

    .io_ddrA_r_payload_last             (axi_inter_s0_rlast                      ),
    .io_ddrA_r_payload_resp             (axi_inter_s0_rresp                      ),
    .io_ddrA_r_payload_id               (axi_inter_s0_rid                        ),
    .io_ddrA_r_payload_data             (axi_inter_s0_rdata                      ),
    .io_ddrA_r_ready                    (axi_inter_s0_rready                     ),
    .io_ddrA_r_valid                    (axi_inter_s0_rvalid                     ),
    
    //custom instruction
    .cpu0_customInstruction_cmd_valid   (cpu_customInstruction_cmd_valid),
    .cpu0_customInstruction_cmd_ready   (cpu_customInstruction_cmd_ready),
    .cpu0_customInstruction_function_id (cpu_customInstruction_function_id),
    .cpu0_customInstruction_inputs_0    (cpu_customInstruction_inputs_0),
    .cpu0_customInstruction_inputs_1    (cpu_customInstruction_inputs_1),
    .cpu0_customInstruction_rsp_valid   (cpu_customInstruction_rsp_valid),
    .cpu0_customInstruction_rsp_ready   (cpu_customInstruction_rsp_ready),
    .cpu0_customInstruction_outputs_0   (cpu_customInstruction_outputs_0),
     //SPI 0
    .system_spi_0_io_sclk_write         (system_spi_0_io_sclk_write         ),
    .system_spi_0_io_data_0_writeEnable (system_spi_0_io_data_0_writeEnable ),
    .system_spi_0_io_data_0_read        (system_spi_0_io_data_0_read        ),
    .system_spi_0_io_data_0_write       (system_spi_0_io_data_0_write       ),
    .system_spi_0_io_data_1_writeEnable (system_spi_0_io_data_1_writeEnable ),
    .system_spi_0_io_data_1_read        (system_spi_0_io_data_1_read        ),
    .system_spi_0_io_data_1_write       (system_spi_0_io_data_1_write       ),
    .system_spi_0_io_data_2_writeEnable (system_spi_0_io_data_2_writeEnable),
    .system_spi_0_io_data_2_read        (system_spi_0_io_data_2_read),
    .system_spi_0_io_data_2_write       (system_spi_0_io_data_2_write),
    .system_spi_0_io_data_3_writeEnable (system_spi_0_io_data_3_writeEnable),
    .system_spi_0_io_data_3_read        (system_spi_0_io_data_3_read),
    .system_spi_0_io_data_3_write       (system_spi_0_io_data_3_write),
    .system_spi_0_io_ss                 (system_spi_0_io_ss                 ),
    //APB 0
    .io_apbSlave_0_PADDR                (apb_paddr                          ),
    .io_apbSlave_0_PSEL                 (apb_psel                           ),
    .io_apbSlave_0_PENABLE              (apb_penable                        ),
    .io_apbSlave_0_PREADY               (apb_pready                         ),
    .io_apbSlave_0_PWRITE               (apb_pwrite                         ),
    .io_apbSlave_0_PWDATA               (apb_pwdata                         ),
    .io_apbSlave_0_PRDATA               (apb_prdata                         ),
    .io_apbSlave_0_PSLVERROR            (apb_pslverror                      ),
    .userInterruptA                     (userInterruptA),
    .userInterruptB                     (userInterruptB),

`ifdef RISCV_SOFT_JTAG
    //Soft Jtag Tap
    .io_jtag_tms                        (io_jtag_tms                        ),
    .io_jtag_tdi                        (io_jtag_tdi                        ),
    .io_jtag_tdo                        (io_jtag_tdo                        ),
    .io_jtag_tck                        (io_jtag_tck                        )
`else
    //Hard Jtag Tap
    .jtagCtrl_tck                       (jtag_inst1_TCK                     ),
    .jtagCtrl_tdi                       (jtag_inst1_TDI                     ),
    .jtagCtrl_tdo                       (jtag_inst1_TDO                     ),
    .jtagCtrl_enable                    (jtag_inst1_SEL                     ),
    .jtagCtrl_capture                   (jtag_inst1_CAPTURE                 ),
    .jtagCtrl_shift                     (jtag_inst1_SHIFT                   ),
    .jtagCtrl_update                    (jtag_inst1_UPDATE                  ),
    .jtagCtrl_reset                     (jtag_inst1_RESET                   )
`endif
);


tinyml_top#(
  .AXI_DW             (AXI_TINYML_DATA_WIDTH)
) u_tinyml_top(
   .clk              (i_sysclk),
   .reset            (io_systemReset),
   .cmd_valid        (cpu_customInstruction_cmd_valid),
   .cmd_ready        (cpu_customInstruction_cmd_ready),
   .cmd_function_id  (cpu_customInstruction_function_id),
   .cmd_inputs_0     (cpu_customInstruction_inputs_0),
   .cmd_inputs_1     (cpu_customInstruction_inputs_1),
   .cmd_int          (cpu_customInstruction_cmd_int),
   .rsp_valid        (cpu_customInstruction_rsp_valid),
   .rsp_ready        (cpu_customInstruction_rsp_ready),
   .rsp_outputs_0    (cpu_customInstruction_outputs_0),
   .m_axi_clk        (io_memoryClk),
   .m_axi_rstn       (!io_systemReset),
   .m_axi_awvalid    (axi_inter_s2_awvalid),
   .m_axi_awaddr     (axi_inter_s2_awaddr),
   .m_axi_awlen      (axi_inter_s2_awlen),
   .m_axi_awsize     (axi_inter_s2_awsize),
   .m_axi_awburst    (axi_inter_s2_awburst),
   .m_axi_awprot     (axi_inter_s2_awprot),
   .m_axi_awlock     (axi_inter_s2_awlock),
   .m_axi_awcache    (axi_inter_s2_awcache),
   .m_axi_awready    (axi_inter_s2_awready),
   .m_axi_wdata      (axi_inter_s2_wdata),
   .m_axi_wstrb      (axi_inter_s2_wstrb),
   .m_axi_wlast      (axi_inter_s2_wlast),
   .m_axi_wvalid     (axi_inter_s2_wvalid),
   .m_axi_wready     (axi_inter_s2_wready),
   .m_axi_bresp      (axi_inter_s2_bresp),
   .m_axi_bvalid     (axi_inter_s2_bvalid),
   .m_axi_bready     (axi_inter_s2_bready),
   .m_axi_arvalid    (axi_inter_s2_arvalid),
   .m_axi_araddr     (axi_inter_s2_araddr),
   .m_axi_arlen      (axi_inter_s2_arlen),
   .m_axi_arsize     (axi_inter_s2_arsize),
   .m_axi_arburst    (axi_inter_s2_arburst),
   .m_axi_arprot     (axi_inter_s2_arprot),
   .m_axi_arlock     (axi_inter_s2_arlock),
   .m_axi_arcache    (axi_inter_s2_arcache),
   .m_axi_arready    (axi_inter_s2_arready),
   .m_axi_rvalid     (axi_inter_s2_rvalid),
   .m_axi_rdata      (axi_inter_s2_rdata),
   .m_axi_rlast      (axi_inter_s2_rlast),
   .m_axi_rresp      (axi_inter_s2_rresp),
   .m_axi_rready     (axi_inter_s2_rready)
);

wire [0:0] c2_cpu_awvalid;
wire [0:0] c2_cpu_awready;
wire [31:0] c2_cpu_awaddr;
wire [7:0] c2_cpu_awlen;
wire [0:0] c2_cpu_wvalid;
wire [0:0] c2_cpu_wready;
wire [127:0] c2_cpu_wdata;
wire [15:0] c2_cpu_wstrb;
wire [0:0] c2_cpu_wlast;
wire [0:0] c2_cpu_bvalid;
wire [0:0] c2_cpu_bready;
wire [1:0] c2_cpu_bresp;
wire [0:0] c2_cpu_arvalid;
wire [0:0] c2_cpu_arready;
wire [31:0] c2_cpu_araddr;
wire [7:0] c2_cpu_arlen;
wire [0:0] c2_cpu_rvalid;
wire [0:0] c2_cpu_rready;
wire [127:0] c2_cpu_rdata;
wire [0:0] c2_cpu_rlast;
wire [1:0] c2_cpu_rresp;
wire  c2_v_frame_valid;
wire  c2_v_frame_ready;
wire [511:0] c2_v_descriptor;
wire  c2_v_grant_valid;
wire  c2_v_grant_ready;
wire [31:0] c2_v_grant_frame_id;
wire  c2_v_word_valid;
wire  c2_v_word_ready;
wire [127:0] c2_v_word_data;
wire  c2_v_source_valid;
wire  c2_v_source_ready;
wire  c2_v_source_error;
wire [31:0] c2_v_source_frame_id;
wire  c2_v_event_valid;
wire  c2_v_event_ready;
wire [2:0] c2_v_event_status;
wire  c2_v_event_slot;
wire [31:0] c2_v_event_generation;
wire [511:0] c2_v_event_descriptor;
wire [31:0] c2_v_source_fnv;
wire  c2_video_awvalid;
wire  c2_video_awready;
wire [31:0] c2_video_awaddr;
wire [7:0] c2_video_awlen;
wire  c2_video_wvalid;
wire  c2_video_wready;
wire [127:0] c2_video_wdata;
wire [15:0] c2_video_wstrb;
wire  c2_video_wlast;
wire  c2_video_bvalid;
wire  c2_video_bready;
wire [1:0] c2_video_bresp;
wire  c2_video_arvalid;
wire  c2_video_arready;
wire [31:0] c2_video_araddr;
wire [7:0] c2_video_arlen;
wire  c2_video_rvalid;
wire  c2_video_rready;
wire [127:0] c2_video_rdata;
wire  c2_video_rlast;
wire [1:0] c2_video_rresp;
wire [4-1:0] c2_video_awid;
wire [2:0] c2_video_awsize;
wire [1:0] c2_video_awburst;
wire  c2_video_awlock;
wire [4-1:0] c2_video_arid;
wire [2:0] c2_video_arsize;
wire [1:0] c2_video_arburst;
wire  c2_video_arlock;
wire [4-1:0] c2_video_bid;
wire [4-1:0] c2_video_rid;
axi_interconnect_beta #(
    .S_COUNT                            (3                                                 ),
    .SLAVE_ASYN_ARRAY                   ({1'b0,1'b0,1'b0}                                  ),
    .S_AXI_DW_ARRAY                     ({AXI_TINYML_DATA_WIDTH,AXI_DATA_WIDTH,AXI_DATA_WIDTH}    ),
    .CB_DW                              (AXI_DATA_WIDTH                                    ),
    .M_AXI_DW                           (AXI_DATA_WIDTH                                    ),
    .ARB_MODE                           (1                                                 ),
    .FAMILY                             ("TITANIUM"                                        ),
    .RD_QUEUE_FIFO_RAM_STYLE            ("block_ram"                                       ),
    .RD_QUEUE_FIFO_DEPTH                (256                                               )
) u_axi_interconnect (
   //AXI slave interfaces - S0: Connected to RISC-V SoC; S1: Connected to DMA controller; S2: Connected to TinyML accelerator
   .s_axi_clk       ({io_memoryClk         , io_memoryClk        , io_memoryClk        }),
   .s_axi_rstn      ({!io_systemReset      , !io_systemReset     , !io_systemReset     }),
   .s_axi_awaddr     ({axi_inter_s2_awaddr , axi_inter_s1_awaddr , c2_cpu_awaddr }),
   .s_axi_awlen      ({axi_inter_s2_awlen  , axi_inter_s1_awlen  , c2_cpu_awlen  }),
   .s_axi_awvalid    ({axi_inter_s2_awvalid, axi_inter_s1_awvalid, c2_cpu_awvalid}),
   .s_axi_awready    ({axi_inter_s2_awready, axi_inter_s1_awready, c2_cpu_awready}),
   .s_axi_wdata      ({axi_inter_s2_wdata  , axi_inter_s1_wdata  , c2_cpu_wdata  }),
   .s_axi_wstrb      ({axi_inter_s2_wstrb  , axi_inter_s1_wstrb  , c2_cpu_wstrb  }),
   .s_axi_wlast      ({axi_inter_s2_wlast  , axi_inter_s1_wlast  , c2_cpu_wlast  }),
   .s_axi_wvalid     ({axi_inter_s2_wvalid , axi_inter_s1_wvalid , c2_cpu_wvalid }),
   .s_axi_wready     ({axi_inter_s2_wready , axi_inter_s1_wready , c2_cpu_wready }),
   .s_axi_bresp      ({axi_inter_s2_bresp  , axi_inter_s1_bresp  , c2_cpu_bresp  }),
   .s_axi_bvalid     ({axi_inter_s2_bvalid , axi_inter_s1_bvalid , c2_cpu_bvalid }),
   .s_axi_bready     ({axi_inter_s2_bready , axi_inter_s1_bready , c2_cpu_bready }),
   .s_axi_araddr     ({axi_inter_s2_araddr , axi_inter_s1_araddr , c2_cpu_araddr }),
   .s_axi_arlen      ({axi_inter_s2_arlen  , axi_inter_s1_arlen  , c2_cpu_arlen  }),
   .s_axi_arvalid    ({axi_inter_s2_arvalid, axi_inter_s1_arvalid, c2_cpu_arvalid}),
   .s_axi_arready    ({axi_inter_s2_arready, axi_inter_s1_arready, c2_cpu_arready}),
   .s_axi_rdata      ({axi_inter_s2_rdata  , axi_inter_s1_rdata  , c2_cpu_rdata  }),
   .s_axi_rresp      ({axi_inter_s2_rresp  , axi_inter_s1_rresp  , c2_cpu_rresp  }),
   .s_axi_rlast      ({axi_inter_s2_rlast  , axi_inter_s1_rlast  , c2_cpu_rlast  }),
   .s_axi_rvalid     ({axi_inter_s2_rvalid , axi_inter_s1_rvalid , c2_cpu_rvalid }),
   .s_axi_rready     ({axi_inter_s2_rready , axi_inter_s1_rready , c2_cpu_rready }),
   //AXI master interface - Connect to HyperRAM controller
   .m_axi_clk        (io_memoryClk),
   .m_axi_rstn       (!io_systemReset),

   .m_axi_awid       (axi_inter_m_awid),
   .m_axi_awaddr     (axi_inter_m_awaddr),
   .m_axi_awlen      (axi_inter_m_awlen),
   .m_axi_awsize     (axi_inter_m_awsize),
   .m_axi_awburst    (axi_inter_m_awburst),
   .m_axi_awlock     (axi_inter_m_awlock),
   .m_axi_awcache    (axi_inter_m_awcache),
   .m_axi_awprot     (axi_inter_m_awprot),
   .m_axi_awvalid    (axi_inter_m_awvalid),
   .m_axi_awready    (axi_inter_m_awready),
   .m_axi_wdata      (axi_inter_m_wdata),
   .m_axi_wstrb      (axi_inter_m_wstrb),
   .m_axi_wlast      (axi_inter_m_wlast),
   .m_axi_wvalid     (axi_inter_m_wvalid),
   .m_axi_wready     (axi_inter_m_wready),
   .m_axi_bresp      (axi_inter_m_bresp),
   .m_axi_bvalid     (axi_inter_m_bvalid),
   .m_axi_bready     (axi_inter_m_bready),
   .m_axi_arid       (axi_inter_m_arid),
   .m_axi_araddr     (axi_inter_m_araddr),
   .m_axi_arlen      (axi_inter_m_arlen),
   .m_axi_arsize     (axi_inter_m_arsize),
   .m_axi_arburst    (axi_inter_m_arburst),
   .m_axi_arlock     (axi_inter_m_arlock),
   .m_axi_arcache    (axi_inter_m_arcache),
   .m_axi_arprot     (axi_inter_m_arprot),
   .m_axi_arvalid    (axi_inter_m_arvalid),
   .m_axi_arready    (axi_inter_m_arready),
   .m_axi_rdata      (axi_inter_m_rdata),
   .m_axi_rresp      (axi_inter_m_rresp),
   .m_axi_rlast      (axi_inter_m_rlast),
   .m_axi_rvalid     (axi_inter_m_rvalid),
   .m_axi_rready     (axi_inter_m_rready)
);
c2_axi_to_vendor #(.ALLOW_NARROW(1),.SOURCE_BASE(32'h1000),
 .TARGET_BASE(32'h1000),.WINDOW_BYTES(32'he0000000)) c2_cpu_adapter(
.clk(io_memoryClk),.rst_n(c2_mem_release[1]),.enable(1'b1),
.s_awvalid(axi_inter_s0_awvalid),
.s_awready(axi_inter_s0_awready),
.s_awaddr(axi_inter_s0_awaddr),
.s_awlen(axi_inter_s0_awlen),
.s_wvalid(axi_inter_s0_wvalid),
.s_wready(axi_inter_s0_wready),
.s_wdata(axi_inter_s0_wdata),
.s_wstrb(axi_inter_s0_wstrb),
.s_wlast(axi_inter_s0_wlast),
.s_bvalid(axi_inter_s0_bvalid),
.s_bready(axi_inter_s0_bready),
.s_bresp(axi_inter_s0_bresp),
.s_arvalid(axi_inter_s0_arvalid),
.s_arready(axi_inter_s0_arready),
.s_araddr(axi_inter_s0_araddr),
.s_arlen(axi_inter_s0_arlen),
.s_rvalid(axi_inter_s0_rvalid),
.s_rready(axi_inter_s0_rready),
.s_rdata(axi_inter_s0_rdata),
.s_rlast(axi_inter_s0_rlast),
.s_rresp(axi_inter_s0_rresp),
.s_awid(axi_inter_s0_awid),
.s_arid(axi_inter_s0_arid),
.s_bid(axi_inter_s0_bid),
.s_rid(axi_inter_s0_rid),
.s_awsize(axi_inter_s0_awsize),
.s_arsize(axi_inter_s0_arsize),
.s_awburst(axi_inter_s0_awburst),
.s_arburst(axi_inter_s0_arburst),
.s_awlock(axi_inter_s0_awlock),
.s_arlock(axi_inter_s0_arlock),
.m_awvalid(c2_cpu_awvalid),
.m_awready(c2_cpu_awready),
.m_awaddr(c2_cpu_awaddr),
.m_awlen(c2_cpu_awlen),
.m_wvalid(c2_cpu_wvalid),
.m_wready(c2_cpu_wready),
.m_wdata(c2_cpu_wdata),
.m_wstrb(c2_cpu_wstrb),
.m_wlast(c2_cpu_wlast),
.m_bvalid(c2_cpu_bvalid),
.m_bready(c2_cpu_bready),
.m_bresp(c2_cpu_bresp),
.m_arvalid(c2_cpu_arvalid),
.m_arready(c2_cpu_arready),
.m_araddr(c2_cpu_araddr),
.m_arlen(c2_cpu_arlen),
.m_rvalid(c2_cpu_rvalid),
.m_rready(c2_cpu_rready),
.m_rdata(c2_cpu_rdata),
.m_rlast(c2_cpu_rlast),
.m_rresp(c2_cpu_rresp),
.rejected(c2_cpu_rejected),.protocol_error(c2_cpu_protocol_error));
c2_vendor_attachment #(.REQUIRE_SOURCE_COMPLETION(1)) c2_attachment(
.arst_n(!io_systemReset),.mem_clk(io_memoryClk),.video_clk(c2_video_clk),.pclk(i_peripheralClk),.map_enable(c2_map_enable),
.external_protocol_error(c2_cpu_rejected || c2_cpu_protocol_error),
.shared_video_ms(c2_shared_video_ms),.shared_video_valid(c2_shared_video_valid),
.shared_cpu_ms(c3_shared_ms),.shared_cpu_valid(c3_shared_valid),
.paddr(apb_paddr),.psel(apb_psel && !c3_page),.penable(apb_penable),.pwrite(apb_pwrite),.pwdata(apb_pwdata),
.pready(c2_apb_ready),.prdata(c2_apb_prdata),.pslverror(c2_apb_error),.irq(c2_irq),
.video_awvalid(c2_video_awvalid),
.video_awready(c2_video_awready),
.video_awaddr(c2_video_awaddr),
.video_awlen(c2_video_awlen),
.video_wvalid(c2_video_wvalid),
.video_wready(c2_video_wready),
.video_wdata(c2_video_wdata),
.video_wstrb(c2_video_wstrb),
.video_wlast(c2_video_wlast),
.video_bvalid(c2_video_bvalid),
.video_bready(c2_video_bready),
.video_bresp(c2_video_bresp),
.video_arvalid(c2_video_arvalid),
.video_arready(c2_video_arready),
.video_araddr(c2_video_araddr),
.video_arlen(c2_video_arlen),
.video_rvalid(c2_video_rvalid),
.video_rready(c2_video_rready),
.video_rdata(c2_video_rdata),
.video_rlast(c2_video_rlast),
.video_rresp(c2_video_rresp),
.video_awid(c2_video_awid),
.video_awsize(c2_video_awsize),
.video_awburst(c2_video_awburst),
.video_awlock(c2_video_awlock),
.video_arid(c2_video_arid),
.video_arsize(c2_video_arsize),
.video_arburst(c2_video_arburst),
.video_arlock(c2_video_arlock),
.video_bid(c2_video_bid),
.video_rid(c2_video_rid),
.v_frame_valid(c2_v_frame_valid),
.v_frame_ready(c2_v_frame_ready),
.v_descriptor(c2_v_descriptor),
.v_grant_valid(c2_v_grant_valid),
.v_grant_ready(c2_v_grant_ready),
.v_grant_frame_id(c2_v_grant_frame_id),
.v_word_valid(c2_v_word_valid),
.v_word_ready(c2_v_word_ready),
.v_word_data(c2_v_word_data),
.v_source_valid(c2_v_source_valid),
.v_source_ready(c2_v_source_ready),
.v_source_error(c2_v_source_error),
.v_source_frame_id(c2_v_source_frame_id),
.v_event_valid(c2_v_event_valid),
.v_event_ready(c2_v_event_ready),
.v_event_status(c2_v_event_status),
.v_event_slot(c2_v_event_slot),
.v_event_generation(c2_v_event_generation),
.v_event_descriptor(c2_v_event_descriptor),
.v_source_fnv(c2_v_source_fnv),
.m_awvalid(axi_inter_s1_awvalid),
.m_awready(axi_inter_s1_awready),
.m_awaddr(axi_inter_s1_awaddr),
.m_awlen(axi_inter_s1_awlen),
.m_awsize(),
.m_awburst(),
.m_wvalid(axi_inter_s1_wvalid),
.m_wready(axi_inter_s1_wready),
.m_wdata(axi_inter_s1_wdata),
.m_wstrb(axi_inter_s1_wstrb),
.m_wlast(axi_inter_s1_wlast),
.m_bvalid(axi_inter_s1_bvalid),
.m_bready(axi_inter_s1_bready),
.m_bresp(axi_inter_s1_bresp),
.m_arvalid(axi_inter_s1_arvalid),
.m_arready(axi_inter_s1_arready),
.m_araddr(axi_inter_s1_araddr),
.m_arlen(axi_inter_s1_arlen),
.m_arsize(),
.m_arburst(),
.m_rvalid(axi_inter_s1_rvalid),
.m_rready(axi_inter_s1_rready),
.m_rdata(axi_inter_s1_rdata),
.m_rlast(axi_inter_s1_rlast),
.m_rresp(axi_inter_s1_rresp),
.protocol_error(c2_protocol_error));
c3_apb_peripheral c3_peripheral(
.arst_n(!io_systemReset),.pclk(i_peripheralClk),.io_enable(c3_io_enable),
.shared_ms(c3_shared_ms),.shared_valid(c3_shared_valid),
.scl_i(c3_sensor_scl_read),.sda_i(c3_sensor_sda_read),
.scl_drive_low(c3_sensor_scl_drive_low),.sda_drive_low(c3_sensor_sda_drive_low),
.buzzer(c3_buzzer),.alarm_led(c3_alarm_led),
.paddr(apb_paddr[7:0]),.psel(apb_psel && c3_page),.penable(apb_penable),.pwrite(apb_pwrite),.pwdata(apb_pwdata),
.pready(c3_apb_ready),.prdata(c3_apb_prdata),.pslverror(c3_apb_error));
c2_a_video_source #(.FRAME_WIDTH(C2_FRAME_WIDTH),.FRAME_HEIGHT(C2_FRAME_HEIGHT),
.STEP_X(C2_STEP_X),.STEP_Y(C2_STEP_Y)) c2_video_source(
.arst_n(!io_systemReset),.video_clk(c2_video_clk),.enable(c2_map_enable),
.pixel_vs(c2_pixel_vs),.pixel_de(c2_pixel_de),.pixel_gray(c2_pixel_gray),
.shared_now_ms(c2_shared_video_ms),.shared_time_valid(c2_shared_video_valid),
.capture_config_valid(c2_capture_config_valid),
.capture_record_valid(c2_capture_record_valid),.capture_record_complete(c2_capture_record_complete),
.capture_record_frame_id(c2_capture_record_frame_id),.capture_record_timestamp_ms(c2_capture_record_timestamp_ms),
.capture_record_width(c2_capture_record_width),.capture_record_height(c2_capture_record_height),
.capture_source_frames(c2_capture_source_frames),.capture_format_errors(c2_capture_format_errors),
.v_frame_valid(c2_v_frame_valid),
.v_frame_ready(c2_v_frame_ready),
.v_descriptor(c2_v_descriptor),
.v_grant_valid(c2_v_grant_valid),
.v_grant_ready(c2_v_grant_ready),
.v_grant_frame_id(c2_v_grant_frame_id),
.v_word_valid(c2_v_word_valid),
.v_word_ready(c2_v_word_ready),
.v_word_data(c2_v_word_data),
.v_source_valid(c2_v_source_valid),
.v_source_ready(c2_v_source_ready),
.v_source_error(c2_v_source_error),
.v_source_frame_id(c2_v_source_frame_id),
.v_source_fnv(c2_v_source_fnv),
.v_event_valid(c2_v_event_valid),
.v_event_ready(c2_v_event_ready),
.v_event_status(c2_v_event_status),
.v_event_descriptor(c2_v_event_descriptor),
.completed(c2_a_completed),.rejected(c2_a_rejected),.source_faults(c2_a_source_faults),
.source_commits(),.source_drops(),.source_malformed(),.last_frame_id(),.last_sum32(),.last_fnv(),.last_status());
c2_video_pipeline #(.WIDTH(C2_FRAME_WIDTH),.HEIGHT(C2_FRAME_HEIGHT)) c2_full_video(
.arst_n(!io_systemReset),.mem_clk(io_memoryClk),.video_clk(c2_video_clk),.display_clk(c2_display_clk),
.enable(c2_map_enable),.time_valid(c2_shared_video_valid && c2_capture_config_valid),
.pixel_vs(c2_pixel_vs),.pixel_de(c2_pixel_de),.pixel_gray(c2_pixel_gray),
.now_ms(c2_shared_video_ms),.source_frames(c2_capture_source_frames),
.record_valid(c2_capture_record_valid),.record_complete(c2_capture_record_complete),
.record_id(c2_capture_record_frame_id),.record_ms(c2_capture_record_timestamp_ms),
.display_vs(c2_display_vs),.display_de(c2_display_de),.display_hs(c2_display_hs),
.display_rgb(c2_display_rgb),.out_vs(c2_out_vs),.out_de(c2_out_de),.out_hs(c2_out_hs),
.display_busy(c2_display_busy),.display_available(c2_display_available),.display_failed(c2_display_failed),
.display_frame_id(c2_display_frame_id),.display_timestamp_ms(c2_display_timestamp_ms),
.published(c2_video_published),
.dropped(c2_video_dropped),
.overflow_frames(c2_video_overflow_frames),
.write_errors(c2_video_write_errors),
.read_errors(c2_video_read_errors),
.repeated(c2_video_repeated),
.empty_scans(c2_video_empty_scans),
.underflows(c2_video_underflows),
.missed_scans(c2_video_missed_scans),
.completed_scans(c2_video_completed_scans),
.max_aw_wait(c2_video_max_aw_wait),
.max_ar_wait(c2_video_max_ar_wait),
.awvalid(c2_video_awvalid),
.awready(c2_video_awready),
.awaddr(c2_video_awaddr),
.awlen(c2_video_awlen),
.wvalid(c2_video_wvalid),
.wready(c2_video_wready),
.wdata(c2_video_wdata),
.wstrb(c2_video_wstrb),
.wlast(c2_video_wlast),
.bvalid(c2_video_bvalid),
.bready(c2_video_bready),
.bresp(c2_video_bresp),
.arvalid(c2_video_arvalid),
.arready(c2_video_arready),
.araddr(c2_video_araddr),
.arlen(c2_video_arlen),
.rvalid(c2_video_rvalid),
.rready(c2_video_rready),
.rdata(c2_video_rdata),
.rlast(c2_video_rlast),
.rresp(c2_video_rresp));
assign c2_video_awid=4'he;assign c2_video_arid=4'h7;
assign c2_video_awsize=3'd4;assign c2_video_arsize=3'd4;
assign c2_video_awburst=2'b01;assign c2_video_arburst=2'b01;
assign c2_video_awlock=1'b0;assign c2_video_arlock=1'b0;
endmodule
